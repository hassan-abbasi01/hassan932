# Docker Setup Guide for FYP Video Processing App

## 🐳 What is Docker?
Docker packages your entire application (code, dependencies, FFmpeg, MongoDB) into containers. One command starts everything!

## 💰 Is Docker Free?
**YES!** Docker Desktop is FREE for:
- Personal use
- Educational projects (your FYP)
- Small businesses (<250 employees, <$10M revenue)

## 📥 Installation

### Windows
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install and restart your computer
3. Open Docker Desktop and wait for it to start
4. Verify installation:
   ```powershell
   docker --version
   docker-compose --version
   ```

## 🚀 Running with Docker

### Quick Start (All Services)
```powershell
# Start everything (MongoDB + Backend + Frontend)
docker-compose up

# Start in background (detached mode)
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v
```

### Access Your App
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5001/api
- **MongoDB**: localhost:27017

### Useful Commands
```powershell
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild containers (after code changes)
docker-compose build
docker-compose up --build

# Stop a specific service
docker-compose stop backend

# Restart a service
docker-compose restart backend

# Execute commands in container
docker-compose exec backend python init_db.py
docker-compose exec backend bash
```

## 🔄 Both Methods Still Work!

### Method 1: Docker (Recommended)
```powershell
docker-compose up
```
✅ Everything configured automatically
✅ No FFmpeg path issues
✅ MongoDB included
✅ One command to start

### Method 2: Normal Way (Still Works!)
```powershell
# Terminal 1: MongoDB (if installed locally)
mongod

# Terminal 2: Backend
cd backend
python app.py

# Terminal 3: Frontend
npm run dev
```
✅ Your current setup unchanged
✅ No Docker required

## 🛠️ Development Workflow with Docker

### Hot Reload Enabled
Code changes are reflected automatically:
- **Backend**: Just save Python files, Flask auto-reloads
- **Frontend**: Rebuild needed (or use dev mode below)

### Development Mode (with hot reload)
For frontend development with instant updates:
```powershell
# Start only MongoDB and Backend with Docker
docker-compose up mongodb backend

# Run frontend normally (in another terminal)
npm run dev
```

## 📦 What's Included?

### Backend Container
- Python 3.11
- FFmpeg (pre-installed, no path issues!)
- All Python packages from requirements.txt
- Uploads folder mounted (files persist)

### Frontend Container
- Node.js 18
- Nginx web server
- Optimized production build
- Auto-handles React routing

### MongoDB Container
- MongoDB 7.0
- Data persisted in Docker volume
- Accessible on port 27017

## 🐛 Troubleshooting

### Port Already in Use
```powershell
# Check what's using the port
netstat -ano | findstr :5001
netstat -ano | findstr :27017

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml
```

### Cannot Connect to Docker
```powershell
# Make sure Docker Desktop is running
# Check Docker status
docker ps

# Restart Docker Desktop
```

### Fresh Start
```powershell
# Remove everything and start clean
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### View Container Details
```powershell
# List running containers
docker ps

# View all containers
docker ps -a

# Inspect a container
docker inspect fyp-backend
```

## 🌐 Using with Ngrok

Docker and ngrok work together perfectly:

```powershell
# Start Docker services
docker-compose up -d

# In another terminal, expose backend
ngrok http 5001
```

## 📊 Resource Usage

Docker is lightweight:
- **MongoDB**: ~50MB RAM
- **Backend**: ~200-500MB RAM (depending on video processing)
- **Frontend**: ~20MB RAM

## 🎓 When to Use Which Method?

### Use Docker When:
- ✅ Setting up on a new machine
- ✅ Deploying to production
- ✅ Working in a team
- ✅ Want hassle-free setup

### Use Normal Method When:
- ✅ Quick debugging
- ✅ Testing small changes
- ✅ Docker Desktop is slow on your PC
- ✅ You prefer your current workflow

## 🚢 Deployment Ready

Your Docker setup is ready for:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform
- Heroku
- Railway.app

Just push your code and deploy!

## 📝 Environment Variables

Create a `.env` file in the root:
```env
JWT_SECRET_KEY=your-super-secret-key-here
VITE_API_URL=http://localhost:5001/api
```

Docker will automatically use these.

## ✨ Benefits Summary

1. **No More Setup Headaches**: One command, everything works
2. **FFmpeg Just Works**: No path configuration needed
3. **Team Friendly**: Share with anyone, works the same
4. **Production Ready**: Same container works everywhere
5. **Easy Rollback**: Version control your entire infrastructure
6. **Resource Efficient**: Containers are lightweight
7. **Isolated**: No conflicts with other projects

---

**Need Help?** 
- Docker Docs: https://docs.docker.com/
- Docker Desktop Download: https://www.docker.com/products/docker-desktop/

**Your current setup is NOT affected!** You can switch between Docker and normal method anytime.
