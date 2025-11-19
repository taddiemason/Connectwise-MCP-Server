#!/bin/bash

# ConnectWise MCP Server Test Script

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ConnectWise MCP Server Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Check if .env exists
echo -e "${BLUE}Test 1: Checking .env configuration...${NC}"
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file found${NC}"
    
    # Check if credentials are set
    if grep -q "your_company_id_here" .env; then
        echo -e "${RED}✗ .env file still contains default values${NC}"
        echo -e "${YELLOW}  Please update .env with your ConnectWise credentials${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ .env file appears configured${NC}"
    fi
else
    echo -e "${RED}✗ .env file not found${NC}"
    echo -e "${YELLOW}  Run: cp .env.example .env${NC}"
    exit 1
fi
echo ""

# Test 2: Check Docker
echo -e "${BLUE}Test 2: Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker is installed${NC}"
else
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose is installed${NC}"
else
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi
echo ""

# Test 3: Check if containers are running
echo -e "${BLUE}Test 3: Checking container status...${NC}"
if docker ps | grep -q "connectwise-mcp-bridge"; then
    echo -e "${GREEN}✓ MCP Bridge container is running${NC}"
else
    echo -e "${YELLOW}⚠ MCP Bridge container is not running${NC}"
    echo -e "${YELLOW}  Run: docker-compose up -d${NC}"
fi

if docker ps | grep -q "connectwise-mcp-server"; then
    echo -e "${GREEN}✓ MCP Server container is running${NC}"
else
    echo -e "${YELLOW}⚠ MCP Server container is not running${NC}"
    echo -e "${YELLOW}  Run: docker-compose up -d${NC}"
fi
echo ""

# Test 4: Health check
echo -e "${BLUE}Test 4: Testing health endpoint...${NC}"
response=$(curl -s http://localhost:3002/health 2>/dev/null)
if [ $? -eq 0 ]; then
    if echo "$response" | grep -q "ok"; then
        echo -e "${GREEN}✓ Health endpoint responding correctly${NC}"
        echo -e "  Response: $response"
    else
        echo -e "${RED}✗ Unexpected health response${NC}"
        echo -e "  Response: $response"
    fi
else
    echo -e "${RED}✗ Health endpoint not responding${NC}"
    echo -e "${YELLOW}  Make sure containers are running: docker-compose ps${NC}"
fi
echo ""

# Test 5: Test API call
echo -e "${BLUE}Test 5: Testing API endpoint...${NC}"
test_payload='{"tool_name": "connectwise_get_companies", "arguments": {"pageSize": 1}}'
response=$(curl -s -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d "$test_payload" 2>/dev/null)

if [ $? -eq 0 ]; then
    if echo "$response" | grep -q "error"; then
        echo -e "${YELLOW}⚠ API call returned an error${NC}"
        echo -e "  This might indicate authentication issues"
        echo -e "  Error: $(echo $response | head -c 200)"
    else
        echo -e "${GREEN}✓ API endpoint responding${NC}"
        echo -e "  Successfully connected to ConnectWise"
    fi
else
    echo -e "${RED}✗ API endpoint not responding${NC}"
fi
echo ""

# Test 6: Check logs for errors
echo -e "${BLUE}Test 6: Checking for errors in logs...${NC}"
if docker-compose logs --tail=50 2>&1 | grep -i "error\|failed\|exception" | head -5 > /tmp/cw_errors.txt; then
    if [ -s /tmp/cw_errors.txt ]; then
        echo -e "${YELLOW}⚠ Found errors in logs:${NC}"
        cat /tmp/cw_errors.txt
    else
        echo -e "${GREEN}✓ No critical errors found in recent logs${NC}"
    fi
else
    echo -e "${GREEN}✓ No critical errors found${NC}"
fi
rm -f /tmp/cw_errors.txt
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. If all tests passed, add connectwise_tools.py to OpenWebUI"
echo "2. Configure the bridge URL in OpenWebUI Valves"
echo "3. Try asking: 'Show me all open tickets'"
echo ""
echo "For troubleshooting:"
echo "- View logs: docker-compose logs -f"
echo "- Check status: docker-compose ps"
echo "- Restart: docker-compose restart"
echo ""
