## Clipboard Image Integration (/c command)
- If the user executes the `/c` command and the output contains "Image captured.", you must **immediately** use the `read_file` tool to read the image path specified in the command (usually `.gemini/tmp/clipboard_image.png`).
- There is no need to wait for a `/v` command (image reading instruction) from the user. Proactively read the image and understand its contents.
- After reading, return a short response such as "I have confirmed the image" and wait for the user's question.
