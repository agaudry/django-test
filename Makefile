run: ## Run the test server.
	python manage.py runserver_plus

install: ## Install the python requirements.
	pip install -r requirements.txt

migrate: ## Apply migrations.
	python manage.py migrate

makemigrations: ## Create new migrations based on the models.
	python manage.py makemigrations

create_admin_user: ## Create a superuser for the admin interface.
	python manage.py createsuperuser