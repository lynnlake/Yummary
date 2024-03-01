from flask import Flask

app = Flask(__name__)

@app.route("/")
def yummary():
    return "<p>Hello, Yummary!</p>"

if __name__ == "__main__":
    app.run(debug=True)