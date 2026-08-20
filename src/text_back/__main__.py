from text_back.app import create_app

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("text_back.__main__:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
