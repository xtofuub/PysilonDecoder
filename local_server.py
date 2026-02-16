from http.server import HTTPServer

from api.decode import handler as DecodeHandler


def main() -> None:
    server = HTTPServer(("localhost", 8000), DecodeHandler)
    print("Server running at http://localhost:8000")
    print("Open index.html in your browser and upload a zip.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
