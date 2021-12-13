"""
Simple RESTful client that forks TermSuite and collects extracted terms.
A Java version would be more efficient...
"""
import os
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config.from_object("config")


@app.route('/extract', methods=['POST'])
def extract():
    text = request.get_json().get("text")
    ts_cmd = Path(app.config["TS_CMD"])
    if not ts_cmd.is_absolute():
        ts_cmd = Path(app.root_path) / ts_cmd
    with tempfile.TemporaryDirectory(prefix="ts") as temp:
        corpus = Path(temp)
        corpus_fr = corpus / "fr"
        corpus_fr.mkdir()
        with open(corpus_fr / "all.txt", "w", encoding="utf8") as txt_out:
            txt_out.write(text)
        ts_output = corpus / "all.tsv"
        ts = [str(ts_cmd), corpus.absolute().as_posix(), ts_output.absolute().as_posix()]
        try:
            subprocess.run(ts, capture_output=True, check=True)
        except subprocess.CalledProcessError as ex:
            app.logger.warning("TermSuite failed: command %s returned %s", ex.cmd, ex.stderr)
            return jsonify({"err": ex.returncode, "stderr": str(ex.stderr)}), 500
        terms = fields = []
        if ts_output.exists():
            with open(ts_output, "r", encoding="utf8") as ts:
                for line in ts.readlines():
                    line = line.strip()
                    if line.startswith("#") and not fields:
                        fields = line.split("\t")
                    else:
                        extracted = line.split("\t")
                        data = {}
                        for i, d in enumerate(extracted):
                            if i > 0:
                                data[fields[i]] = d
                        terms.append(data)
        return jsonify(terms)
