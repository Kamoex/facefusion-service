#!/usr/bin/env python3

import time
import logging
import service
from flask import Flask, jsonify, request
from const_define import *

app = Flask(__name__)
srv = service.my_service()



@app.route("/", methods=["POST"])
def post_handler():
    res_json = E_SUCESS
    try:
        body = request.get_json()
        res_json = srv.post_handle(body)
    except Exception as e:
        logging.info("post request error: " + str(e))
    return jsonify(res_json)
    # core.cli()

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=7860)
