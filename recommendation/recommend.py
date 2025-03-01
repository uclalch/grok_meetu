import pandas as pd
from surprise import SVD, Dataset, Reader, dump
from surprise.model_selection import train_test_split
from pathlib import Path
import datetime
import argparse
import json
from surprise import accuracy

class RecommendationSystem:
    def __init__(self, users, chatrooms, interactions):
        self.users = users
        self.chatrooms = chatrooms
        self.interactions = interactions
        self.model = None
        self.model_dir = Path("/Users/larryli/Documents/Sobriety/Companies/grok_meetu/recommendation/models")
        self.model_dir.mkdir(exist_ok=True)
    
    def _get_latest_model_path(self) -> Path:
        """Get the path of today's model file if it exists"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        return self.model_dir / f"model_{today}.pkl"
    
    def load_model(self):
        """Load the latest trained model"""
        model_path = self._get_latest_model_path()
        if not model_path.exists():
            raise ValueError(f"No trained model found for today at {model_path}")
        print(f"Loading model from {model_path}")
        _, self.model = dump.load(str(model_path))
    
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
        model_path = self._get_latest_model_path()
        version_info = self._load_version_info(model_path)
        return version_info.get('timestamp', 'unknown')

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
        data = Dataset.load_from_df(self.interactions[["user_id", "chatroom_id", "satisfaction_score"]], reader)
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
        
        return test_predictions

    def predict(self, user_id, chatroom_id):
        if self.model is None:
            raise ValueError("Model not trained yet.")
        
        prediction = self.model.predict(user_id, chatroom_id).est
        version = self._get_model_version()
        
        # Log prediction
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'model_version': version,
            'user_id': user_id,
            'chatroom_id': chatroom_id,
            'prediction': float(prediction)
        }
        
        # Append to log file
        log_path = self.model_dir / 'predictions.jsonl'
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return prediction

    def calculate_derived_features(self, user_id, chatroom_id):
        user = self.users[self.users["user_id"] == user_id].iloc[0]
        chatroom = self.chatrooms[self.chatrooms["chatroom_id"] == chatroom_id].iloc[0]
        
        # Motivation match
        user_interests = set(user["interests"])
        chatroom_topics = set(chatroom["topics"])
        intersection = len(user_interests & chatroom_topics)
        union = len(user_interests | chatroom_topics)
        motivation_match = intersection / union if union > 0 else 0
        
        # Pressure compatibility
        pressure_compatibility = 0.9 if user["level_of_pressure"] < 3 and chatroom["vibe_score"] > 3 else 0.6
        
        # Credit access level
        credit_score = user["platform_credit_score"]
        credit_access_level = "full" if credit_score > 80 else "partial" if credit_score > 50 else "limited"
        
        return {
            "motivation_match": motivation_match,
            "pressure_compatibility": pressure_compatibility,
            "credit_access_level": credit_access_level
        }

    def get_recommendations(self, user_id, motivation_threshold=0.1, pressure_threshold=0.7, required_credit_level="partial"):
        joined_chatrooms = self.interactions[self.interactions["user_id"] == user_id]["chatroom_id"].tolist()
        to_predict = [cid for cid in self.chatrooms["chatroom_id"] if cid not in joined_chatrooms]
        
        recommendations = []
        for chatroom_id in to_predict:
            pred_score = self.predict(user_id, chatroom_id)
            derived = self.calculate_derived_features(user_id, chatroom_id)
            if (derived["motivation_match"] > motivation_threshold and
                derived["pressure_compatibility"] > pressure_threshold and
                derived["credit_access_level"] == required_credit_level):
                recommendations.append((chatroom_id, pred_score))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Train recommendation model')
    parser.add_argument('--force', action='store_true', 
                       help='Force training even if model exists for today')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='Test set size for model evaluation')
    args = parser.parse_args()

    # Updated Users Data (only U2's interests modified)
    users = pd.DataFrame({
        "user_id": ["U1", "U2", "U3"],
        "interests": [["travel", "tech"], ["art", "relax", "gaming"], ["gaming", "music"]],
        "level_of_pressure": [2, 1, 3],
        "platform_credit_score": [92, 68, 85]
    })

    chatrooms = pd.DataFrame({
        "chatroom_id": ["C1", "C2", "C3"],
        "name": ["AI Travel Planners", "Artistic Chill Zone", "Indie Game Devs"],
        "topics": [["AI", "travel"], ["art", "relax"], ["gaming", "coding"]],
        "vibe_score": [4, 5, 4]
    })

    interactions = pd.DataFrame({
        "user_id": ["U1", "U2", "U3"],
        "chatroom_id": ["C1", "C2", "C3"],
        "satisfaction_score": [5, 4, 5]
    })

    # Run the system
    rec_sys = RecommendationSystem(users, chatrooms, interactions)
    rec_sys.train_model(force=args.force, test_size=args.test_size)
    recommendations = rec_sys.get_recommendations("U2")

    # Print the recommendations
    print("Recommendations for U2:")
    for chatroom_id, score in recommendations:
        chatroom_name = chatrooms[chatrooms["chatroom_id"] == chatroom_id]["name"].values[0]
        print(f"- {chatroom_name}: Predicted Satisfaction = {score:.2f}")