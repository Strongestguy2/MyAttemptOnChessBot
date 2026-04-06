FROM python:3.11

WORKDIR /app

# Good defaults
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CHESSBOT_GUI=0

# Copy dependency file first if you have one
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . /app

CMD ["python", "main.py"]