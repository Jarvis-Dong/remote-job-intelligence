FROM apify/actor-python:3.13

USER myuser
COPY --chown=myuser:myuser requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=myuser:myuser remote_job_intelligence ./remote_job_intelligence
COPY --chown=myuser:myuser .actor ./.actor
RUN python -m compileall -q remote_job_intelligence

CMD ["python", "-m", "remote_job_intelligence"]
