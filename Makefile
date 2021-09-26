.PHONY: imagerun imageapp docks3 docksql pythons3 pythonsql pythonflask dockergoogle

imagerun:
	docker build -t chmsia423 .

imageapp:
	docker build -f Dockerfile_app -t chmsia423 .

docks3: run.py
	docker run -it -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY chmsia423 run.py ingests3

docksql: run.py
	docker run -it -e MYSQL_HOST -e MYSQL_PORT -e MYSQL_USER -e MYSQL_PASSWORD -e MYSQL_DATABASE -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY chmsia423 run.py s3rds

dockerflask: app.py
	docker run -it -p 5000:5000 -e MYSQL_HOST -e MYSQL_PORT -e MYSQL_USER -e MYSQL_PASSWORD -e MYSQL_DATABASE -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY chmsia423 app.py

dockergoogle: run.py
	docker run -it -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY chmsia423 run.py fgoogle

pythons3: run.py
	python3 run.py ingests3

pythonsql: run.py
	python3 run.py s3rds
