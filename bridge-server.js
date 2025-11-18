/**
 * ConnectWise MCP Bridge Server
 * Exposes HTTP API for OpenWebUI to communicate with ConnectWise MCP server
 */

const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.MCP_PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'connectwise-mcp-bridge'
  });
});

// MCP tool execution endpoint
app.post('/v1/tools/execute', async (req, res) => {
  const { tool_name, arguments: toolArguments } = req.body;

  if (!tool_name) {
    return res.status(400).json({ error: 'tool_name is required' });
  }

  console.log(`Executing tool: ${tool_name}`);
  console.log(`Arguments:`, JSON.stringify(toolArguments, null, 2));

  try {
    // Spawn the MCP server process
    const mcpProcess = spawn('python', ['connectwise_mcp.py']);

    let stdout = '';
    let stderr = '';

    // Build MCP request
    const mcpRequest = {
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/call',
      params: {
        name: tool_name,
        arguments: toolArguments || {}
      }
    };

    // Send request to MCP server
    mcpProcess.stdin.write(JSON.stringify(mcpRequest) + '\n');
    mcpProcess.stdin.end();

    // Collect stdout
    mcpProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    // Collect stderr
    mcpProcess.stderr.on('data', (data) => {
      stderr += data.toString();
      console.error('MCP stderr:', data.toString());
    });

    // Handle process completion
    mcpProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`MCP process exited with code ${code}`);
        console.error('stderr:', stderr);
        return res.status(500).json({
          error: 'MCP server error',
          details: stderr
        });
      }

      try {
        // Parse MCP response
        const lines = stdout.trim().split('\n');
        let mcpResponse = null;

        // Find the JSON-RPC response line
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);
            if (parsed.jsonrpc === '2.0' && parsed.id === 1) {
              mcpResponse = parsed;
              break;
            }
          } catch (e) {
            // Skip non-JSON lines
          }
        }

        if (!mcpResponse) {
          throw new Error('No valid MCP response found');
        }

        if (mcpResponse.error) {
          return res.status(500).json({
            error: mcpResponse.error.message || 'MCP error',
            code: mcpResponse.error.code
          });
        }

        // Extract result from MCP response
        const result = mcpResponse.result;
        
        // Parse the text content if it's JSON
        if (result && result.content && Array.isArray(result.content)) {
          const textContent = result.content.find(c => c.type === 'text');
          if (textContent) {
            try {
              const parsedData = JSON.parse(textContent.text);
              return res.json(parsedData);
            } catch (e) {
              // Return as plain text if not JSON
              return res.json({ data: textContent.text });
            }
          }
        }

        res.json(result);
      } catch (error) {
        console.error('Error parsing MCP response:', error);
        console.error('stdout:', stdout);
        res.status(500).json({
          error: 'Failed to parse MCP response',
          details: error.message
        });
      }
    });

    // Handle process errors
    mcpProcess.on('error', (error) => {
      console.error('Failed to start MCP process:', error);
      res.status(500).json({
        error: 'Failed to start MCP server',
        details: error.message
      });
    });

  } catch (error) {
    console.error('Error in tool execution:', error);
    res.status(500).json({
      error: 'Internal server error',
      details: error.message
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`ConnectWise MCP Bridge listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Execute endpoint: POST http://localhost:${PORT}/v1/tools/execute`);
});
