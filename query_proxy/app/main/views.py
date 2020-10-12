from flask import abort, request

from . import main


@main.route("/", methods=["GET", "POST"])
def index():
    warnings = []
    query = {}
    if not "request" in request.args:
        # raise 400: Bad Request
        abort(400, description="Query terms are missing. Expected 'request' parameter.")
    if "start" in request.args:
        try:
            start = int(request.args["start"])
            query["start"] = start
        except ValueError as e:
            warnings.append(f"Could not parse 'start' parameter: {e.args[0]}")
    if "end" in request.args:
        try:
            end = int(request.args["end"])
            query["end"] = end
        except ValueError as e:
            warnings.append(f"Could not parse 'end' parameter: {e.args[0]}")
    if "size" in request.args:
        try:
            size = int(request.args["size"])
        except ValueError as e:
            warnings.append(f"Could not parse 'size' parameter: {e.args[0]}")
            size = 10
    else:
        size = 10
    query["size"] = size
    if "sort" in request.args:
        sort = request.args["sort"].strip().lower()
        if sort in ("asc", "desc"):
            query["sort"] = sort
        else:
            warnings.append(
                f"Unknown sorting parameter '{sort}'. Expected 'asc' or 'desc'."
            )
    answer = "\n".join(f"{key}: {value}" for key, value in request.args.items())

    return answer
