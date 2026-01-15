FROM python:3.12.3-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set the default command to run the parser
# You can override the HL7 file by passing it as an argument
ENTRYPOINT ["python3", "-m", "hl7_siu_parser.hl7_parser"]
CMD ["test_message.hl7"]