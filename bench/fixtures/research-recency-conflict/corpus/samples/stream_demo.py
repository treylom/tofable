# requires driftwood-sdk>=5.2
# minimal example: streaming a completion from /v1/complete
#
# see changelog-2026-05.md (v5.2) for details on the stream=true parameter.

from driftwood import Client

client = Client(token="YOUR_TOKEN")


def main():
    stream = client.complete(
        prompt="Summarize the attached report in three bullet points.",
        stream=True,
    )

    for chunk in stream:
        print(chunk.text, end="", flush=True)

    print()  # newline once the stream ends


if __name__ == "__main__":
    main()
