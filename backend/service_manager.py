import subprocess
import time
import logging
import os
import signal
import psutil
import socket
from colorama import init, Fore, Style
import requests
from requests.exceptions import RequestException

# Initialize colorama for colored output
init()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_port_in_use(port):
    """Check if port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_process_by_port(port):
    """Find process using specified port"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr.port == port:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.Error):
            continue
    return None

def kill_process_on_port(port):
    """Kill process using specified port"""
    if is_port_in_use(port):
        logger.info(f"Port {port} is in use, stopping process...")
        proc = find_process_by_port(port)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except psutil.Error as e:
                logger.warning(f"Error terminating process on port {port}: {e}")
                try:
                    proc.kill()  # Force kill if terminate fails
                except psutil.Error:
                    pass

def wait_for_url(url, timeout=30):
    """Wait for a URL to become available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url)
            return True
        except RequestException:
            time.sleep(1)
    return False

def find_and_kill_node_process():
    """Find and kill any node processes running the React app"""
    try:
        # On macOS/Linux
        subprocess.run(["pkill", "-f", "react-scripts start"], 
                      stderr=subprocess.DEVNULL)
    except:
        pass

def kill_docker_container(image_name):
    """Kill docker container by image name"""
    try:
        containers = subprocess.check_output(
            ["docker", "ps", "-q", "--filter", f"ancestor={image_name}"]
        ).decode().strip()
        
        if containers:
            subprocess.run(["docker", "stop", containers.split('\n')],
                         stderr=subprocess.DEVNULL)
    except:
        pass

class ServiceManager:
    def __init__(self):
        self.processes = {}
        
    def print_service_info(self):
        """Print service endpoints in a clear format"""
        print("\n" + "="*50)
        print(f"{Fore.GREEN}✓ All Services Started Successfully!{Style.RESET_ALL}")
        print("="*50)
        print(f"{Fore.YELLOW}Frontend:{Style.RESET_ALL}    http://localhost:3000")
        print(f"{Fore.YELLOW}Backend API:{Style.RESET_ALL} http://localhost:8000")
        print(f"{Fore.YELLOW}Admin API:{Style.RESET_ALL}   http://localhost:8001")
        print(f"{Fore.YELLOW}ScyllaDB:{Style.RESET_ALL}    localhost:9042")
        print("="*50)
        print(f"{Fore.CYAN}Commands:{Style.RESET_ALL}")
        print(f"- Use {Fore.WHITE}grok-stop{Style.RESET_ALL} to stop all services")
        print(f"- Use {Fore.WHITE}grok-restart{Style.RESET_ALL} to restart all services")
        print("="*50 + "\n")
        
    def cleanup_processes(self):
        """Thorough cleanup of all processes"""
        print(f"{Fore.YELLOW}→ Cleaning up existing processes...{Style.RESET_ALL}")
        
        # Kill any React processes
        find_and_kill_node_process()
        
        # Kill processes on specific ports
        kill_process_on_port(8000)  # Backend
        kill_process_on_port(3000)  # Frontend
        
        # Stop ScyllaDB containers
        kill_docker_container("scylladb/scylla")
        
        # Give processes time to shut down
        time.sleep(2)
    
    def clean_frontend_install(self, frontend_dir):
        """Clean and reinstall frontend dependencies"""
        print(f"{Fore.YELLOW}→ Cleaning frontend installation...{Style.RESET_ALL}")
        try:
            # Remove node_modules and package-lock.json
            subprocess.run(["rm", "-rf", "node_modules", "package-lock.json"], 
                         cwd=frontend_dir, check=True)
            
            # Clean npm cache
            subprocess.run(["npm", "cache", "clean", "--force"], 
                         cwd=frontend_dir, check=True)
            
            # Install dependencies with faster options
            print(f"{Fore.YELLOW}→ Installing frontend dependencies (this may take a few minutes)...{Style.RESET_ALL}")
            install_proc = subprocess.Popen(
                ["npm", "install", "--prefer-offline", "--no-audit", "--progress"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Show progress and implement timeout
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            while install_proc.poll() is None:
                if time.time() - start_time > timeout:
                    install_proc.terminate()
                    raise Exception("npm install timed out after 5 minutes")
                
                print(".", end='', flush=True)
                time.sleep(1)
            
            if install_proc.returncode != 0:
                out, err = install_proc.communicate()
                print(f"\n{Fore.RED}Error during npm install:{Style.RESET_ALL}")
                if out: print(f"Output: {out}")
                if err: print(f"Error: {err}")
                raise Exception("npm install failed")
            
            print(f"\n{Fore.GREEN}✓ Dependencies installed successfully!{Style.RESET_ALL}")
            
            # Install critical dependencies explicitly
            print(f"{Fore.YELLOW}→ Installing additional dependencies...{Style.RESET_ALL}")
            subprocess.run([
                "npm", "install", "--save",
                "js-tokens@4.0.0",
                "@babel/code-frame@7.22.13",
                "fork-ts-checker-webpack-plugin@6.5.3",
                "react-dev-utils@12.0.1"
            ], cwd=frontend_dir, check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}Error during clean install: {e}{Style.RESET_ALL}")
            raise Exception("Failed to clean install frontend dependencies")

    def setup_frontend(self, frontend_dir):
        """Set up frontend directory structure and files"""
        print(f"{Fore.YELLOW}→ Setting up frontend structure...{Style.RESET_ALL}")
        
        # Create directories
        os.makedirs(os.path.join(frontend_dir, "public"), exist_ok=True)
        os.makedirs(os.path.join(frontend_dir, "src"), exist_ok=True)
        
        # Create index.html
        index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="Grok MeetU - Recommendation System" />
    <title>Grok MeetU</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
"""
        with open(os.path.join(frontend_dir, "public", "index.html"), "w") as f:
            f.write(index_html)
            
        # Create manifest.json
        manifest_json = """{
  "short_name": "Grok MeetU",
  "name": "Grok MeetU Recommendation System",
  "start_url": ".",
  "display": "standalone",
  "theme_color": "#000000",
  "background_color": "#ffffff"
}
"""
        with open(os.path.join(frontend_dir, "public", "manifest.json"), "w") as f:
            f.write(manifest_json)
            
        # Create index.js
        index_js = 'import React from "react";\n' + \
                   'import ReactDOM from "react-dom/client";\n' + \
                   'import "./App.css";\n' + \
                   'import App from "./App";\n\n' + \
                   'const root = ReactDOM.createRoot(document.getElementById("root"));\n' + \
                   'root.render(\n' + \
                   '  <React.StrictMode>\n' + \
                   '    <App />\n' + \
                   '  </React.StrictMode>\n' + \
                   ');\n'
        
        with open(os.path.join(frontend_dir, "src", "index.js"), "w") as f:
            f.write(index_js)
            
        # Create App.js
        app_js = 'import React, { useState } from "react";\n' + \
                 'import axios from "axios";\n' + \
                 'import "./App.css";\n\n' + \
                 'function App() {\n' + \
                 '  const [userId, setUserId] = useState("");\n' + \
                 '  const [recommendations, setRecommendations] = useState([]);\n' + \
                 '  const [loading, setLoading] = useState(false);\n' + \
                 '  const [error, setError] = useState(null);\n\n' + \
                 '  const handleSubmit = async (e) => {\n' + \
                 '    e.preventDefault();\n' + \
                 '    setLoading(true);\n' + \
                 '    setError(null);\n\n' + \
                 '    try {\n' + \
                 '      const response = await axios.post("http://localhost:8000/recommendations", {\n' + \
                 '        user_id: userId\n' + \
                 '      });\n' + \
                 '      setRecommendations(response.data.recommendations || []);\n' + \
                 '    } catch (err) {\n' + \
                 '      setError(err.response?.data?.detail || "Failed to get recommendations");\n' + \
                 '    } finally {\n' + \
                 '      setLoading(false);\n' + \
                 '    }\n' + \
                 '  };\n\n' + \
                 '  return (\n' + \
                 '    <div className="App">\n' + \
                 '      <h1>Grok MeetU</h1>\n' + \
                 '      <div className="container">\n' + \
                 '        <form onSubmit={handleSubmit}>\n' + \
                 '          <input\n' + \
                 '            type="text"\n' + \
                 '            value={userId}\n' + \
                 '            onChange={(e) => setUserId(e.target.value)}\n' + \
                 '            placeholder="Enter User ID"\n' + \
                 '            required\n' + \
                 '          />\n' + \
                 '          <button type="submit" disabled={loading}>\n' + \
                 '            {loading ? "Loading..." : "Get Recommendations"}\n' + \
                 '          </button>\n' + \
                 '        </form>\n\n' + \
                 '        {error && <div className="error">{error}</div>}\n\n' + \
                 '        {recommendations.length > 0 && (\n' + \
                 '          <div className="recommendations">\n' + \
                 '            <h2>Recommended Chatrooms</h2>\n' + \
                 '            <div className="cards">\n' + \
                 '              {recommendations.map((rec) => (\n' + \
                 '                <div key={rec.chatroom_id} className="card">\n' + \
                 '                  <h3>Chatroom {rec.chatroom_id}</h3>\n' + \
                 '                  <div className="score">Score: {rec.predicted_score.toFixed(2)}</div>\n' + \
                 '                </div>\n' + \
                 '              ))}\n' + \
                 '            </div>\n' + \
                 '          </div>\n' + \
                 '        )}\n' + \
                 '      </div>\n' + \
                 '    </div>\n' + \
                 '  );\n' + \
                 '}\n\n' + \
                 'export default App;\n'

        with open(os.path.join(frontend_dir, "src", "App.js"), "w") as f:
            f.write(app_js)
            
        # Create App.css
        app_css = """.App {
  text-align: center;
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.container {
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #333;
  margin-bottom: 30px;
}

form {
  margin-bottom: 20px;
}

input {
  padding: 10px;
  font-size: 16px;
  margin-right: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 200px;
}

button {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background-color: #ccc;
}

.error {
  color: #dc3545;
  margin: 10px 0;
}

.recommendations {
  margin-top: 30px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  padding: 20px;
}

.card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.card h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.score {
  color: #007bff;
  font-weight: bold;
}
"""
        with open(os.path.join(frontend_dir, "src", "App.css"), "w") as f:
            f.write(app_css)

    def start_services(self):
        """Start all services"""
        print(f"\n{Fore.CYAN}Starting Grok MeetU Services...{Style.RESET_ALL}")
        
        try:
            # Thorough cleanup first
            self.cleanup_processes()
            
            # Start ScyllaDB
            print(f"{Fore.YELLOW}→ Starting ScyllaDB...{Style.RESET_ALL}")
            scylla_proc = subprocess.Popen(
                ["docker", "run", "--rm", "-p", "9042:9042", "scylladb/scylla"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes['scylla'] = scylla_proc
            
            # Wait for ScyllaDB
            print(f"{Fore.YELLOW}→ Waiting for ScyllaDB to be ready...{Style.RESET_ALL}")
            time.sleep(10)  # ScyllaDB needs time to initialize
            
            # Start Backend
            print(f"{Fore.YELLOW}→ Starting FastAPI backend...{Style.RESET_ALL}")
            backend_proc = subprocess.Popen(
                ["uvicorn", "backend.app:app", "--reload", "--port", "8000", "--log-level", "info"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            self.processes['backend'] = backend_proc

            # Start Admin API
            print(f"{Fore.YELLOW}→ Starting Admin API...{Style.RESET_ALL}")
            admin_proc = subprocess.Popen(
                ["uvicorn", "backend.admin_app:admin_app", "--reload", "--port", "8001", "--log-level", "info"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            self.processes['admin'] = admin_proc
            
            # Wait for backend with progress
            print(f"{Fore.YELLOW}→ Waiting for APIs to be ready...{Style.RESET_ALL}", end='', flush=True)
            for _ in range(30):
                if (wait_for_url("http://localhost:8000", timeout=1) and 
                    wait_for_url("http://localhost:8001", timeout=1)):
                    print(f"\r{Fore.GREEN}✓ APIs are ready!{Style.RESET_ALL}")
                    break
                print(".", end='', flush=True)
                time.sleep(1)
            else:
                raise Exception("APIs failed to start")
            
            # Start Frontend
            frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
            
            # Check if npm is installed
            try:
                subprocess.run(["npm", "--version"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                raise Exception("npm is not installed. Please install Node.js and npm first.")
            
            # Setup frontend structure if needed
            if not os.path.exists(os.path.join(frontend_dir, "public", "index.html")):
                self.setup_frontend(frontend_dir)
            
            # Install dependencies if needed
            if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
                print(f"{Fore.YELLOW}→ Installing frontend dependencies (this may take a few minutes)...{Style.RESET_ALL}")
                try:
                    subprocess.run(
                        ["npm", "install", "--prefer-offline", "--no-audit"],
                        cwd=frontend_dir,
                        check=True,
                        capture_output=True
                    )
                    print(f"{Fore.GREEN}✓ Dependencies installed successfully!{Style.RESET_ALL}")
                except subprocess.CalledProcessError as e:
                    print(f"{Fore.RED}Error installing dependencies:{Style.RESET_ALL}\n{e.stderr}")
                    raise Exception("Failed to install frontend dependencies")
            
            # Start frontend
            print(f"{Fore.YELLOW}→ Starting React frontend...{Style.RESET_ALL}", end='', flush=True)
            frontend_proc = subprocess.Popen(
                ["npm", "start"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes['frontend'] = frontend_proc
            
            # Wait for frontend with progress and show errors
            for _ in range(60):
                # Check if process is still running
                if frontend_proc.poll() is not None:
                    out, err = frontend_proc.communicate()
                    print(f"\n{Fore.RED}Frontend process exited unexpectedly:{Style.RESET_ALL}")
                    if out: print(f"Output: {out}")
                    if err: print(f"Error: {err}")
                    raise Exception("Frontend process failed to start")
                    
                if wait_for_url("http://localhost:3000", timeout=1):
                    print(f"\r{Fore.GREEN}✓ Frontend is ready!{Style.RESET_ALL}")
                    break
                print(".", end='', flush=True)
                time.sleep(1)
            else:
                out, err = frontend_proc.communicate()
                print(f"\n{Fore.RED}Frontend failed to start:{Style.RESET_ALL}")
                if out: print(f"Output: {out}")
                if err: print(f"Error: {err}")
                raise Exception("Frontend failed to start (timeout)")
            
            print(f"\n{Fore.GREEN}✓ All services started successfully!{Style.RESET_ALL}")
            self.print_service_info()
            
        except Exception as e:
            print(f"\n{Fore.RED}Error starting services: {e}{Style.RESET_ALL}")
            self.stop_services()
            raise

    def stop_services(self):
        """Stop all services"""
        logger.info("Stopping all services...")
        try:
            # Stop Frontend (port 3000)
            kill_process_on_port(3000)
            
            # Stop Backend (port 8000)
            kill_process_on_port(8000)
            
            # Stop ScyllaDB container
            subprocess.run(["docker", "stop", "$(docker ps -q --filter ancestor=scylladb/scylla)"], 
                          shell=True, stderr=subprocess.PIPE)
            
            # Clean up processes
            for name, proc in self.processes.items():
                try:
                    if proc.poll() is None:  # If process is still running
                        proc.terminate()
                        proc.wait(timeout=5)
                except:
                    logger.warning(f"Error terminating {name} process")
            
            self.processes = {}
            print(f"\n{Fore.GREEN}All services stopped successfully{Style.RESET_ALL}\n")
            
        except Exception as e:
            logger.error(f"Error in stop_services: {e}")
            raise

    def restart_services(self):
        """Restart all services"""
        logger.info("Restarting all services...")
        self.stop_services()
        time.sleep(2)
        self.start_services()
        logger.info("All services restarted")

# Create singleton instance
manager = ServiceManager()

# Entry point functions
def start():
    try:
        manager.start_services()
    except Exception as e:
        logger.error(f"Error starting services: {e}")
        raise

def stop():
    try:
        manager.stop_services()
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
        raise

def restart():
    try:
        manager.restart_services()
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        raise 