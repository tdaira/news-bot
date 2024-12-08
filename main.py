import datetime
import json
import os
import sys
import requests
from newsapi import NewsApiClient
from openai import OpenAI
from readabilipy import simple_json_from_html_string
from slack_sdk import WebClient

# Retrieve Job-defined env vars
TASK_INDEX = os.getenv("CLOUD_RUN_TASK_INDEX", 0)
TASK_ATTEMPT = os.getenv("CLOUD_RUN_TASK_ATTEMPT", 0)

# Retrieve User-defined env vars
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANEL = os.getenv("SLACK_CHANEL", "")

def get_function_calling_result(client, function, message):
    tools = [
        {
            "type": "function",
            "function": function
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a bot that extracts important topics from news articles."},
            {
                "role": "user",
                "content": message,
            }
        ],
        tools=tools
    )

    if response.choices[0].finish_reason != 'tool_calls' or response.choices[0].message.tool_calls[0].function.name != function["name"]:
        raise Exception("Cannot find the call result of send_article_title_and_url function.")

    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def get_important_article_id(client, headlines_json):
    function = {
        "name": "send_important_article_id",
        "description": "Send the important article_id to the system.",
        "parameters": {
            "type": "object",
            "properties": {
                "article_ids": {
                    "type": "array",
                    "description": "Array of article_id.",
                    "items": {
                        "type": "integer",
                        "description": "Important article_id."
                    }
                }
            },
            "required": ["article_ids"],
            "additionalProperties": False,
        },
    }

    message = "Please choose 5 important topics from the following headlines. \
        Please read the content carefully and decide its importance. \n```\n" + headlines_json + "\n```"
    return get_function_calling_result(client, function, message)

def get_summarized_article(client, title, content):
    function = {
        "name": "send_summarized_article",
        "description": "Send the summarized article to the system.",
        "parameters": {
            "type": "object",
            "properties": {
                "summarized_article": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the article."
                        },
                        "content": {
                            "type": "string",
                            "description": "The summarized content of the article.",
                            "maxLength": 400
                        }
                    },
                },
            },
            "required": ["summarized_article"],
            "additionalProperties": False,
        },
    }

    message = "下記のtitleとcontentを日本語約してください。contentは400文字以内に要約してください。" + \
        "また、読み手は日本人なので日本人が理解の難しい単語が出てきた場合はその説明も細くしてください。\n\n" + \
        "title:\n" + title + "\n\ncontent:\n" + content
    return get_function_calling_result(client, function, message)

def main():
    print(f"Starting Task #{TASK_INDEX}, Attempt #{TASK_ATTEMPT}...")

    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    top_headlines = newsapi.get_top_headlines(
        category='business',
        page_size=100,
    )

    filtered_headlines = {}
    for i, article in enumerate(top_headlines["articles"]):
        if (article["publishedAt"] is not None and
            article['publishedAt'] >
            datetime.datetime.strftime(
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2), "%Y-%m-%dT%H:%M:%SZ"
            )):
            article['article_id'] = i
            filtered_headlines[i] = article

    headlines_json = json.dumps(filtered_headlines, indent=2)

    client = OpenAI()

    article_ids = get_important_article_id(client, headlines_json)

    slack_client = WebClient(token=SLACK_BOT_TOKEN)

    speech_text = ""
    for article_id in article_ids['article_ids']:
        article = filtered_headlines[article_id]
        print(f"Title: {article['title']}")
        print(f"URL: {article['url']}")
        req = requests.get(article['url'])
        full_article = simple_json_from_html_string(req.text, use_readability=True)
        if full_article['plain_content'] is None:
            continue
        summarized_article = get_summarized_article(client, article['title'], full_article['plain_content'])
        # Send message to Slack
        print(article["urlToImage"])
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANEL,
            text="><" + article['url'] + "|" + summarized_article['summarized_article']['title'] + ">\n" +
                        ">" + summarized_article['summarized_article']['content'],
        )
        speech_text += article["source"]["name"] + "の記事の要約です。\n" + \
            summarized_article['summarized_article']['content'] + "\n\n"

    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="alloy",
        input=speech_text,
    ) as response:
        response.stream_to_file("news.mp3")

    slack_client.files_upload_v2(
        title="news.mp3",
        channel=SLACK_CHANEL,
        file="news.mp3"
    )

    print(f"Completed Task #{TASK_INDEX}.")


# Start script
if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        message = (
            f"Task #{TASK_INDEX}, " + f"Attempt #{TASK_ATTEMPT} failed: {str(err)}"
        )

        print(json.dumps({"message": message, "severity": "ERROR"}))
        sys.exit(1)  # Retry Job Task by exiting the process
