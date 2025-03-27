FROM python:3.13-slim

WORKDIR /app
COPY . .
RUN pip3 install .

CMD ["python3", "stargazer/main.py"]
