# news-bot

## Run in local

```bash
python3 -m venv venv
source ./venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
read NEWS_API_KEY # Enter your NewsAPI API key and press enter
read OPENAI_API_KEY # Enter your OpenAI API key and press enter
read SLACK_BOT_TOKEN # Enter your Slack Bot token and press enter
read SLACK_CHANEL # Enter your Slack channel ID and press enter
export NEWS_API_KEY=$NEWS_API_KEY
export OPENAI_API_KEY=$OPENAI_API_KEY
export SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN
export SLACK_CHANEL=$SLACK_CHANEL
python main.py
```

## Run in Cloud Run

```bash
gcloud run jobs deploy news-bot-job \
    --source . \
    --tasks 1 \
    --set-env-vars NEWS_API_KEY=$NEWS_API_KEY \
    --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
    --set-env-vars SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
    --set-env-vars SLACK_CHANEL=$SLACK_CHANEL \
    --max-retries 1 \
    --region asia-northeast1 \
    --project=<your project id>
gcloud run jobs execute news-bot-job --region asia-northeast1
```
