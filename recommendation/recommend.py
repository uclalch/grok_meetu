import pandas as pd
from surprise import SVD, Dataset, Reader, dump
from surprise.model_selection import train_test_split
from pathlib import Path
import datetime
import argparse
import json
from surprise import accuracy
from cassandra.cluster import Cluster
import logging

logger = logging.getLogger(__name__)

class RecommendationSystem:
    def __init__(self, db_hosts=['localhost'], db_port=9042):
        """Initialize with database connection instead of DataFrames"""
        self.cluster = Cluster(db_hosts, port=db_port)
        self.session = self.cluster.connect('grok_meetu')
        self.model = None
        self.model_dir = Path("/Users/larryli/Documents/Sobriety/Companies/grok_meetu/recommendation/models")
        self.model_dir.mkdir(exist_ok=True)
        self.last_loaded_version = None  # Track last loaded version
    
    def _get_latest_model_path(self) -> Path:
        """Get the path of today's model file if it exists"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        return self.model_dir / f"model_{today}.pkl"
    
    def load_model(self):
        """Load the latest trained model"""
        model_path = self._get_latest_model_path()
        if not model_path.exists():
            raise ValueError(f"No trained model found for today at {model_path}")
        
        logger.info(f"Loading model from {model_path}")
        _, loaded_model = dump.load(str(model_path))
        
        # Get version info for logging
        version_info = self._load_version_info(model_path)
        current_version = version_info.get('timestamp')
        
        logger.info(f"Previous model version: {self.last_loaded_version}")
        logger.info(f"Loading model version: {current_version}")
        
        self.model = loaded_model
        self.last_loaded_version = current_version
        return loaded_model
    
    def _save_version_info(self, model_path: Path, version_info: dict):
        """Save version info separately"""
        version_path = model_path.with_suffix('.version.json')
        with open(version_path, 'w') as f:
            json.dump(version_info, f, indent=2)

    def _load_version_info(self, model_path: Path) -> dict:
        """Load version info"""
        version_path = model_path.with_suffix('.version.json')
        if not version_path.exists():
            return {"timestamp": "unknown", "parameters": {}}
        with open(version_path, 'r') as f:
            return json.load(f)

    def _get_model_version(self) -> str:
        """Get current model version"""
        if self.model is None:
            return None
        return self.last_loaded_version  # Use tracked version instead of reading file

    def _update_model_version(self):
        """Update model version info to force reload"""
        model_path = self._get_latest_model_path()
        if model_path.exists():
            version_info = self._load_version_info(model_path)
            # Update timestamp to force reload
            version_info['timestamp'] = datetime.datetime.now().isoformat()
            self._save_version_info(model_path, version_info)
            logger.info(f"Updated model version to: {version_info['timestamp']}")
            
            # Force model reload
            self.model = None
            self.load_model()
            return True
        return False

    def train_model(self, test_size=0.2, force=False):
        """Train and save a new model"""
        model_path = self._get_latest_model_path()
        
        if model_path.exists() and not force:
            warning_msg = (
                f"\n⚠️  WARNING: Model already exists for today at {model_path}\n"
                f"Current model version: {self._load_version_info(model_path)}\n"
                f"To proceed with training anyway, call train_model(force=True)\n"
            )
            raise ValueError(warning_msg)
        
        print("Training new model...")
        reader = Reader(rating_scale=(1, 5))
        
        # ScyllaDB: Query and convert to DataFrame
        rows = self.session.execute("""
            SELECT user_id, chatroom_id, satisfaction_score 
            FROM interactions
        """)
        interactions_df = pd.DataFrame(rows._current_rows)
        data = Dataset.load_from_df(
            interactions_df[["user_id", "chatroom_id", "satisfaction_score"]], 
            reader
        )
        
        trainset, testset = train_test_split(data, test_size=test_size)
        
        # Train model
        self.model = SVD()
        self.model.fit(trainset)
        
        # Get metrics after training
        test_predictions = self.model.test(testset)
        rmse = accuracy.rmse(test_predictions)
        mae = accuracy.mae(test_predictions)
        
        # Create version info with metrics
        version_info = {
            'timestamp': datetime.datetime.now().isoformat(),
            'test_size': test_size,
            'parameters': {
                'n_factors': 100,
                'n_epochs': 20,
                'lr_all': 0.005,
                'reg_all': 0.02
            },
            'metrics': {
                'rmse': float(rmse),
                'mae': float(mae)
            }
        }
        
        # Save model and version info separately
        dump.dump(str(model_path), algo=self.model)
        self._save_version_info(model_path, version_info)
        print(f"✅ Model saved to {model_path} with version: {version_info['timestamp']}")
        print(f"📊 Model metrics - RMSE: {rmse:.4f}, MAE: {mae:.4f}")
        
        # After saving model, force version update
        self._update_model_version()
        
        return test_predictions

    def predict(self, user_id, chatroom_id):
        if self.model is None:
            raise ValueError("Model not trained yet.")
        
        # Always check for latest model version
        current_path = self._get_latest_model_path()
        if current_path.exists():
            current_version = self._load_version_info(current_path).get('timestamp')
            model_version = self._get_model_version()
            
            # Force reload if versions don't match
            if current_version != model_version:
                logger.info(f"Found newer model version: {current_version}")
                logger.info(f"Current version: {model_version}")
                logger.info("Automatically reloading latest model...")
                self.model = None
                self.load_model()
                logger.info("Model reloaded successfully")
        
        prediction = self.model.predict(user_id, chatroom_id).est
        
        # Log prediction details
        logger.debug(f"Prediction for {user_id} -> {chatroom_id}: {prediction:.2f}")
        logger.debug(f"Using model version: {self._get_model_version()}")
        
        return prediction

    def calculate_derived_features(self, user_id, chatroom_id):
        # Get user data from DB
        user_row = self.session.execute("""
            SELECT interests, level_of_pressure, platform_credit_score 
            FROM users WHERE user_id = %s
        """, (user_id,)).one()
        
        # Get chatroom data from DB
        chatroom_row = self.session.execute("""
            SELECT topics, vibe_score 
            FROM chatrooms WHERE chatroom_id = %s
        """, (chatroom_id,)).one()
        
        # Motivation match
        user_interests = set(user_row.interests)
        chatroom_topics = set(chatroom_row.topics)
        intersection = len(user_interests & chatroom_topics)
        union = len(user_interests | chatroom_topics)
        motivation_match = intersection / union if union > 0 else 0
        
        # Pressure compatibility
        pressure_compatibility = 0.9 if user_row.level_of_pressure < 3 and chatroom_row.vibe_score > 3 else 0.6
        
        # Credit access level
        credit_score = user_row.platform_credit_score
        credit_access_level = "full" if credit_score > 80 else "partial" if credit_score > 50 else "limited"
        
        return {
            "motivation_match": motivation_match,
            "pressure_compatibility": pressure_compatibility,
            "credit_access_level": credit_access_level
        }

    def get_recommendations(self, user_id, motivation_threshold=0.1, pressure_threshold=0.7, required_credit_level="partial"):
        """Get recommendations with detailed logging"""
        logger.info(f"Getting recommendations for user {user_id}")
        
        # Get all chatrooms
        chatroom_rows = self.session.execute("SELECT chatroom_id FROM chatrooms")
        all_chatrooms = [row.chatroom_id for row in chatroom_rows]
        logger.info(f"Found {len(all_chatrooms)} total chatrooms")
        
        # Get joined chatrooms
        joined_rows = self.session.execute(
            "SELECT chatroom_id FROM interactions WHERE user_id = %s", 
            (user_id,)
        )
        joined_chatrooms = [row.chatroom_id for row in joined_rows]
        logger.info(f"User has joined {len(joined_chatrooms)} chatrooms")
        
        # Find chatrooms to predict
        to_predict = [cid for cid in all_chatrooms if cid not in joined_chatrooms]
        logger.info(f"Found {len(to_predict)} chatrooms to predict")
        
        if not to_predict:
            logger.warning("No new chatrooms to recommend")
            return []
        
        recommendations = []
        for chatroom_id in to_predict:
            try:
                pred_score = self.predict(user_id, chatroom_id)
                derived = self.calculate_derived_features(user_id, chatroom_id)
                logger.info(f"Evaluating chatroom {chatroom_id}:")
                logger.info(f"• Motivation match: {derived['motivation_match']:.2f} (threshold: {motivation_threshold})")
                logger.info(f"• Pressure compatibility: {derived['pressure_compatibility']:.2f} (threshold: {pressure_threshold})")
                logger.info(f"• Credit level: {derived['credit_access_level']} (required: {required_credit_level})")
                logger.info(f"• Predicted score: {pred_score:.2f}")
                
                if derived["motivation_match"] <= motivation_threshold:
                    logger.info("❌ Filtered out: Low motivation match")
                elif derived["pressure_compatibility"] <= pressure_threshold:
                    logger.info("❌ Filtered out: Low pressure compatibility")
                elif derived["credit_access_level"] != required_credit_level:
                    logger.info("❌ Filtered out: Wrong credit level")
                else:
                    logger.info("✅ Adding to recommendations")
                    recommendations.append((chatroom_id, pred_score))
            except Exception as e:
                logger.error(f"Error predicting for chatroom {chatroom_id}: {e}")
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Returning {len(recommendations)} recommendations")
        return recommendations

    def _get_data_from_db(self):
        """Get data from ScyllaDB as DataFrames"""
        # Get users
        users_rows = self.session.execute("SELECT * FROM users")
        users_df = pd.DataFrame(users_rows._current_rows)
        
        # Get chatrooms
        chatrooms_rows = self.session.execute("SELECT * FROM chatrooms")
        chatrooms_df = pd.DataFrame(chatrooms_rows._current_rows)
        
        # Get interactions
        interactions_rows = self.session.execute("SELECT * FROM interactions")
        interactions_df = pd.DataFrame(interactions_rows._current_rows)
        
        return users_df, chatrooms_df, interactions_df

if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Train or run inference with recommendation model')
    parser.add_argument('--mode', choices=['train', 'infer'], default='infer',
                       help='Mode to run: train or infer')
    parser.add_argument('--force', action='store_true', 
                       help='Force training even if model exists for today (only with --mode train)')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='Test set size for model evaluation (only with --mode train)')
    parser.add_argument('--user-id', type=str, default="U2",
                       help='User ID for inference (only with --mode infer)')
    args = parser.parse_args()

    # Validate arguments
    if args.mode == 'infer' and args.force:
        print("\n❌ Error: --force can only be used with --mode train")
        exit(1)
    
    if args.mode == 'infer' and args.test_size != 0.2:
        print("\n❌ Warning: --test-size is ignored in infer mode")
    
    if args.mode == 'train' and args.user_id != "U2":
        print("\n❌ Warning: --user-id is ignored in train mode")

    # Run the system
    rec_sys = RecommendationSystem()
    
    if args.mode == 'train':
        rec_sys.train_model(force=args.force, test_size=args.test_size)
    else:  # infer mode
        try:
            rec_sys.load_model()  # Load existing model
            recommendations = rec_sys.get_recommendations(args.user_id)
            
            # Print the recommendations
            print(f"\nRecommendations for {args.user_id}:")
            for chatroom_id, score in recommendations:
                # Get chatroom name from DB instead of DataFrame
                chatroom_row = rec_sys.session.execute("""
                    SELECT name FROM chatrooms WHERE chatroom_id = %s
                """, (chatroom_id,)).one()
                chatroom_name = chatroom_row.name
                print(f"- {chatroom_name}: Predicted Satisfaction = {score:.2f}")
                
            # Print model info
            model_path = rec_sys._get_latest_model_path()
            model_info = rec_sys._load_version_info(model_path)
            print("\nUsing model version:")
            print(f"• Timestamp: {model_info['timestamp']}")
            print(f"• Metrics: RMSE={model_info['metrics']['rmse']:.3f}, MAE={model_info['metrics']['mae']:.3f}")
            
        except ValueError as e:
            print(f"\n❌ Error: {str(e)}")
            print("Hint: Train a model first using --mode train")