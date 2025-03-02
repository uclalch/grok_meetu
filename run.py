# This file is used to run the applications
import uvicorn

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=['user', 'admin'], required=True)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    
    if args.app == 'user':
        uvicorn.run("backend.app:app", host="0.0.0.0", port=args.port, reload=True)
    else:
        uvicorn.run("backend.admin_app:admin_app", host="0.0.0.0", port=args.port, reload=True) 