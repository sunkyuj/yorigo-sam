from flask import Flask, jsonify, request
import handler
import json

app = Flask(__name__)


@app.route("/post", methods=["POST"])
def devide_video():
    if request.method == "POST":
        data = request.json
        if type(data) == str:
            data = json.loads(data)
        recipe_steps = data["recipe_explanations"]
        video_url = data["video_url"]
        recipe_name = data["recipe_title"]

        result = handler.main(recipe_steps, video_url, recipe_name)

        return {"body": json.dumps({"result": result})}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
