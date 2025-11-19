#!/bin/bash

# ConnectWise MCP Server Setup Script

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ConnectWise MCP Server Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

show_menu() {
    echo "Select an option:"
    echo "1. Start ConnectWise MCP Server"
    echo "2. Stop ConnectWise MCP Server"
    echo "3. Restart ConnectWise MCP Server"
    echo "4. View logs"
    echo "5. Check status"
    echo "6. Update server"
    echo "7. Clean up (remove containers and images)"
    echo "8. Exit"
    echo ""
}

start_server() {
    echo -e "${GREEN}Starting ConnectWise MCP Server...${NC}"
    
    # Check if .env exists
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Warning: .env file not found!${NC}"
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${RED}Please edit .env file with your ConnectWise credentials before starting!${NC}"
        exit 1
    fi
    
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Server started successfully!${NC}"
        echo ""
        echo "Bridge API available at: http://localhost:3002"
        echo "Health check: curl http://localhost:3002/health"
    else
        echo -e "${RED}✗ Failed to start server${NC}"
    fi
}

stop_server() {
    echo -e "${YELLOW}Stopping ConnectWise MCP Server...${NC}"
    docker-compose down
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Server stopped successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to stop server${NC}"
    fi
}

restart_server() {
    echo -e "${YELLOW}Restarting ConnectWise MCP Server...${NC}"
    docker-compose restart
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Server restarted successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to restart server${NC}"
    fi
}

view_logs() {
    echo "Select logs to view:"
    echo "1. All logs"
    echo "2. Bridge server logs only"
    echo "3. MCP server logs only"
    echo ""
    read -p "Enter choice [1-3]: " log_choice
    
    case $log_choice in
        1)
            docker-compose logs -f
            ;;
        2)
            docker-compose logs -f mcp-bridge
            ;;
        3)
            docker-compose logs -f connectwise-mcp-server
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

check_status() {
    echo -e "${BLUE}Checking server status...${NC}"
    echo ""
    docker-compose ps
    echo ""
    
    # Test health endpoint
    echo "Testing health endpoint..."
    response=$(curl -s http://localhost:3002/health 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Bridge server is responding${NC}"
        echo "Response: $response"
    else
        echo -e "${RED}✗ Bridge server is not responding${NC}"
    fi
}

update_server() {
    echo -e "${BLUE}Updating ConnectWise MCP Server...${NC}"
    git pull
    docker-compose down
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Server updated successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to update server${NC}"
    fi
}

clean_up() {
    echo -e "${RED}WARNING: This will remove all containers and images!${NC}"
    read -p "Are you sure? (y/N): " confirm
    
    if [[ $confirm == [yY] ]]; then
        echo -e "${YELLOW}Cleaning up...${NC}"
        docker-compose down --rmi all --volumes
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo "Cleanup cancelled"
    fi
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice [1-8]: " choice
    echo ""
    
    case $choice in
        1)
            start_server
            ;;
        2)
            stop_server
            ;;
        3)
            restart_server
            ;;
        4)
            view_logs
            ;;
        5)
            check_status
            ;;
        6)
            update_server
            ;;
        7)
            clean_up
            ;;
        8)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please select 1-8.${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done
