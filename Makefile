.PHONY: all build deploy

STACK_NAME=kordis-cloud

# Define the default action to build and deploy
all: build deploy

# Build by using Docker containers
build:
	@echo "Building the SAM application using Docker containers..."
	sam build --use-container

# Deploy the application
deploy:
	@echo "Deploying the SAM application..."
	sam deploy 

# Deploy the website files to S3 bucket
deploy-site:
	@echo "Deploying the website files..."
	npm run --prefix ./dev-portfolio build
	"C:\Program Files\Amazon\AWSCLIV2\aws" s3 sync ./dev-portfolio/build s3://kordis-cloud --delete

# Run the VisitorCountGetFunction locally
run-VisitorCountGetFunction:
	@echo "Running the VisitorCountGetFunction locally..."
	sam build
	sam local invoke VisitorCountGetFunction 

# Run the VisitorCountPutFunction locally
run-VisitorCountPutFunction:
	@echo "Running the VisitorCountPutFunction locally..."
	sam build
	sam local invoke VisitorCountPutFunction 

# Run python unit tests
unit-tests:
	@echo "Running Python unit tests..."
	pytest -vv tests\unit\test_handler.py

# Run python integration tests
integration-tests:
	@echo "Running Python integration tests..."
	@set AWS_SAM_STACK_NAME=kordis-cloud&& pytest -vv tests/integration/test_api_gateway.py"