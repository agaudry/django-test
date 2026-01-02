run: ## Run the test server.
	python manage.py runserver_plus

install: ## Install the python requirements.
	pip install -r requirements.txt

migrate: ## Apply migrations.
	python manage.py migrate

makemigrations: ## Create new migrations based on the models.
	python manage.py makemigrations

create_admin_user: ## Create a superuser for the admin interface.
	python manage.py createsuperuser --username admin --email admin@test.com

create_data: ## Create initial data.
	python manage.py create_data

test: ## Run all tests.
	python manage.py test padam_django.tests

setup_and_run: install migrate create_data create_admin_user run
