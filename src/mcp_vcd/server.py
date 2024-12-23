from typing import Dict, Optional
import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

server = Server("mcp-vcd")

# Store signal mappings globally since they're constant for a given VCD file
signal_mappings: Dict[str, Dict[str, str]] = {}  # file_name -> {signal_name -> char}

async def parse_signal_mappings(file_name: str) -> Dict[str, str]:
    """Parse VCD file to extract signal name to character mappings."""
    mappings = {}
    try:
        with open(file_name, 'r') as f:
            for line in f:
                if line.startswith('$enddefinitions'):
                    break
                if line.startswith('$var'):
                    parts = line.split()
                    if len(parts) >= 5:
                        char, signal = parts[3], parts[4]
                        mappings[signal] = char
        return mappings
    except Exception as e:
        raise RuntimeError(f"Failed to parse signal mappings: {str(e)}")

async def get_signal_lines(file_name: str, char: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> str:
    """Get all lines containing the specified character within the timestamp range."""
    try:
        matches = []
        current_time = 0
        with open(file_name, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.rstrip()

                # Update current timestamp if we see a timestamp marker
                if line.startswith('#'):
                    try:
                        current_time = int(line[1:])
                    except ValueError:
                        continue

                # Skip if we're before start_time
                if start_time is not None and current_time < start_time:
                    continue

                # Break if we're past end_time
                if end_time is not None and current_time > end_time:
                    break

                # If we're in the desired time range and line contains our character
                if char in line:
                    matches.append(f"{line_num}:{line}")

        return '\n'.join(matches)
    except Exception as e:
        raise RuntimeError(f"Failed to read file: {str(e)}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-signal",
            description="Get all instances of a specified signal in a VCD file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Name of the VCD file to analyze",
                    },
                    "signal_name": {
                        "type": "string",
                        "description": "Name of the signal to search for",
                    },
                    "start_time": {
                        "type": "integer",
                        "description": "Start timestamp (optional)",
                    },
                    "end_time": {
                        "type": "integer",
                        "description": "End timestamp (optional)",
                    },
                },
                "required": ["file_name", "signal_name"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can analyze VCD files and return signal information.
    """
    if not arguments:
        raise ValueError("Missing arguments")

    if name == "get-signal":
        file_name = arguments.get("file_name")
        signal_name = arguments.get("signal_name")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")

        if not file_name or not signal_name:
            raise ValueError("Missing required parameters")

        try:
            # Get or update signal mappings for this file
            if file_name not in signal_mappings:
                signal_mappings[file_name] = await parse_signal_mappings(file_name)

            # Look up the character for this signal
            signal_char = signal_mappings[file_name].get(signal_name)
            if not signal_char:
                return [types.TextContent(
                    type="text",
                    text=f"Signal '{signal_name}' not found in VCD file"
                )]

            # Get all lines containing this character within time range
            output = await get_signal_lines(file_name, signal_char, start_time, end_time)

            return [types.TextContent(
                type="text",
                text=output if output else "No match"
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=str(e)
            )]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-vcd",
                server_version="0.1.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
