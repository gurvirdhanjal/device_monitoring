from app import create_app
import webbrowser
import threading

app = create_app()

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    # Hydrate collector with DB history
    try:
        from routes.monitoring import monitor
        monitor.hydrate_collector(app)
    except Exception as e:
        print(f"Error hydrating collector: {e}")

    threading.Timer(1.5, open_browser).start()
    app.run(host="127.0.0.1", port=5000)
