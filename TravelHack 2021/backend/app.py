from flask import Flask, request
from travel_ranker import Ranker

APPLICATION_NAME = "TravelRanker"


from flask_cors import CORS, cross_origin
app = Flask(APPLICATION_NAME)

ranker = Ranker()

@app.route("/place", methods=["GET"])
def place():
    id_ = request.args.get('id', default=1, type=int)
    return ranker.get_info_by_id(id_), 200

@app.route("/", methods=["GET"])
def default_ranking():
    return ranker.rank(), 200

@app.route("/history", methods=["POST"])
def history_ranking():
    history = request.get_json(force=True)["history"]
    return ranker.rank_with_history(history), 200

@app.errorhandler(404)
def page_is_not_found(error_):
    return "This route is not found", 404

@app.errorhandler(Exception)
def page_is_not_found(error_):
    return "Service is unavailable", 503

def main():
    CORS(app)
    app.run(debug=True)


if __name__ == "__main__":
    main()
