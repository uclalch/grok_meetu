import subprocess
import time
import logging
import argparse
from pathlib import Path
from cassandra.cluster import Cluster
import socket
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SetupManager:
    def __init__(self):
        self.scylla_container = "scylla-db"
        self.api_process = None
        self.cluster = None
        self.session = None
    
    def start_scylla(self):
        """Start ScyllaDB container"""
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.scylla_container}"],
                capture_output=True, text=True
            )
            
            if self.scylla_container in result.stdout:
                logger.info("Starting existing ScyllaDB container...")
                subprocess.run(["docker", "start", self.scylla_container])
            else:
                logger.info("Creating new ScyllaDB container...")
                subprocess.run([
                    "docker", "run", "--name", self.scylla_container,
                    "-p", "9042:9042", "-d", "scylladb/scylla:5.2.0"
                ])
            
            logger.info("Waiting for ScyllaDB to be ready...")
            self.cluster = self._wait_for_db()
            
        except Exception as e:
            logger.error(f"Failed to start ScyllaDB: {e}")
            raise
    
    def _wait_for_db(self):
        """Wait for ScyllaDB to be ready"""
        for _ in range(10):
            try:
                cluster = Cluster(['localhost'], port=9042)
                session = cluster.connect()
                logger.info("Successfully connected to ScyllaDB")
                return cluster
            except Exception as e:
                logger.warning(f"Waiting for ScyllaDB... ({str(e)})")
                time.sleep(5)
        raise Exception("Failed to connect to ScyllaDB")
    
    def setup_database(self):
        """Set up database schema and sample data"""
        try:
            session = self.cluster.connect()

            # Create keyspace
            session.execute("""
                CREATE KEYSPACE IF NOT EXISTS grok_meetu
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
            """)
            session.set_keyspace('grok_meetu')

            # Create tables
            session.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id text PRIMARY KEY,
                    interests list<text>,
                    level_of_pressure int,
                    platform_credit_score int
                )
            """)

            session.execute("""
                CREATE TABLE IF NOT EXISTS chatrooms (
                    chatroom_id text PRIMARY KEY,
                    name text,
                    topics list<text>,
                    vibe_score int
                )
            """)

            session.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    user_id text,
                    chatroom_id text,
                    satisfaction_score int,
                    PRIMARY KEY (user_id, chatroom_id)
                )
            """)

            # Insert sample data
            session.execute("""
                INSERT INTO users (user_id, interests, level_of_pressure, platform_credit_score)
                VALUES ('U1', ['travel', 'tech'], 2, 92)
            """)
            session.execute("""
                INSERT INTO users (user_id, interests, level_of_pressure, platform_credit_score)
                VALUES ('U2', ['art', 'relax', 'gaming'], 1, 68)
            """)
            session.execute("""
                INSERT INTO users (user_id, interests, level_of_pressure, platform_credit_score)
                VALUES ('U3', ['gaming', 'music'], 3, 85)
            """)

            # Insert chatrooms
            session.execute("""
                INSERT INTO chatrooms (chatroom_id, name, topics, vibe_score)
                VALUES ('C1', 'AI Travel Planners', ['AI', 'travel'], 4)
            """)
            session.execute("""
                INSERT INTO chatrooms (chatroom_id, name, topics, vibe_score)
                VALUES ('C2', 'Artistic Chill Zone', ['art', 'relax'], 5)
            """)
            session.execute("""
                INSERT INTO chatrooms (chatroom_id, name, topics, vibe_score)
                VALUES ('C3', 'Indie Game Devs', ['gaming', 'coding'], 4)
            """)

            # Insert interactions
            session.execute("""
                INSERT INTO interactions (user_id, chatroom_id, satisfaction_score)
                VALUES ('U1', 'C1', 5)
            """)
            session.execute("""
                INSERT INTO interactions (user_id, chatroom_id, satisfaction_score)
                VALUES ('U2', 'C2', 4)
            """)
            session.execute("""
                INSERT INTO interactions (user_id, chatroom_id, satisfaction_score)
                VALUES ('U3', 'C3', 5)
            """)

            logger.info("Database setup completed!")

        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def _get_available_port(self, start_port: int) -> int:
        """Get an available port starting from a given port"""
        # Try more ports
        for port in range(start_port, start_port + 20):  # Increased range
            if not self._is_port_in_use(port):
                return port
        raise Exception(f"No available ports found in range {start_port}-{start_port+20}")

    def start_api(self):
        """Start API servers"""
        try:
            # Start user API
            user_port = self._get_available_port(8000)
            self.user_api = subprocess.Popen(
                ["uvicorn", "backend.app:app", "--port", str(user_port)],
                cwd=Path(__file__).parent
            )
            logger.info(f"User API started at http://localhost:{user_port}")
            
            # Start admin API
            admin_port = self._get_available_port(user_port + 1)
            self.admin_api = subprocess.Popen(
                ["uvicorn", "backend.admin_app:admin_app", "--port", str(admin_port)],
                cwd=Path(__file__).parent
            )
            logger.info(f"Admin API started at http://localhost:{admin_port}")
            
        except Exception as e:
            logger.error(f"Failed to start APIs: {e}")
            raise
    
    def stop_all(self):
        """Stop all services"""
        try:
            logger.info("Starting cleanup process...")
            cleanup_status = {"user_api": False, "admin_api": False, "uvicorn": False, "scylla": False}

            # Stop user API
            if hasattr(self, 'user_api'):
                try:
                    self.user_api.terminate()
                    self.user_api.wait(timeout=5)  # Wait for process to terminate
                    cleanup_status["user_api"] = True
                    logger.info("✓ User API stopped successfully")
                except Exception as e:
                    logger.error(f"Failed to stop user API gracefully: {e}")
            
            # Stop admin API
            if hasattr(self, 'admin_api'):
                try:
                    self.admin_api.terminate()
                    self.admin_api.wait(timeout=5)  # Wait for process to terminate
                    cleanup_status["admin_api"] = True
                    logger.info("✓ Admin API stopped successfully")
                except Exception as e:
                    logger.error(f"Failed to stop admin API gracefully: {e}")
            
            # Kill any lingering uvicorn processes
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "uvicorn"], 
                    capture_output=True, 
                    text=True
                )
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    logger.info(f"Found {len(pids)} lingering uvicorn processes")
                    subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
                    cleanup_status["uvicorn"] = True
                    logger.info(f"✓ Cleaned up {len(pids)} uvicorn processes")
                else:
                    logger.info("No lingering uvicorn processes found")
                    cleanup_status["uvicorn"] = True
            except Exception as e:
                logger.warning(f"Failed to clean up uvicorn processes: {e}")
            
            # Stop ScyllaDB
            try:
                # Check if container is running
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={self.scylla_container}"],
                    capture_output=True, text=True
                )
                if self.scylla_container in result.stdout:
                    subprocess.run(["docker", "stop", self.scylla_container])
                    cleanup_status["scylla"] = True
                    logger.info("✓ ScyllaDB container stopped successfully")
                else:
                    logger.info("ScyllaDB container was not running")
                    cleanup_status["scylla"] = True
            except Exception as e:
                logger.warning(f"Failed to stop ScyllaDB container: {e}")
            
            # Print cleanup summary
            logger.info("\nCleanup Summary:")
            for service, success in cleanup_status.items():
                status = "✓ Cleaned" if success else "✗ Failed"
                logger.info(f"{status:10} {service}")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            logger.info("Cleanup process completed")
    
    def show_status(self):
        """Show status of all services"""
        try:
            # Check ScyllaDB
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.scylla_container}"],
                capture_output=True, text=True
            )
            scylla_running = self.scylla_container in result.stdout
            
            # Check API
            api_running = self.api_process is not None and self.api_process.poll() is None
            
            print("\n=== Service Status ===")
            print(f"ScyllaDB: {'🟢 Running' if scylla_running else '🔴 Stopped'}")
            print(f"API Server: {'🟢 Running' if api_running else '🔴 Stopped'}")
            
            # Get actual port being used
            port = 8001  # Default port
            print("\nEndpoints:")
            if api_running:
                print(f"• API Documentation: http://localhost:{port}/docs")
                print(f"• Health Check: http://localhost:{port}/")
                print("\nTest Commands:")
                print(f"curl -X POST 'http://localhost:{port}/recommend' -H 'Content-Type: application/json' -d '{{\"user_id\": \"U1\"}}'")
                print(f"\nTrain Model:")
                print(f"curl -X POST 'http://localhost:{port}/train'")
                print(f"\nModel Info:")
                print(f"curl 'http://localhost:{port}/model-info'")
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")

def main():
    parser = argparse.ArgumentParser(description='Setup and manage services')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'restart'],
                       help='Action to perform')
    parser.add_argument('--skip-db-setup', action='store_true',
                       help='Skip database setup (use existing data)')
    
    args = parser.parse_args()
    manager = SetupManager()
    
    try:
        if args.action in ['start', 'restart']:
            # Always stop existing services first
            manager.stop_all()
            time.sleep(2)  # Wait for processes to clean up
            
            manager.start_scylla()
            if not args.skip_db_setup:
                manager.setup_database()
            manager.start_api()
            manager.show_status()
            
        elif args.action == 'stop':
            manager.stop_all()
            
        elif args.action == 'status':
            manager.show_status()
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        manager.stop_all()
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        manager.stop_all()

if __name__ == "__main__":
    main() 