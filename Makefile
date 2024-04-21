.PHONY: all build deploy

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

# Deploy the website files to S3 bucket, syncing only HTML and CSS files
deploy-site:
	@echo "Deploying the website files..."
	"C:\Program Files\Amazon\AWSCLIV2\aws" s3 sync ./website s3://kordis-cloud 

# Run the VisitorCountGetFunction locally
run-VisitorCountGetFunction:
	@echo "Running the VisitorCountGetFunction locally..."
	sam local invoke VisitorCountGetFunction --event events/event.json

# Run the VisitorCountPutFunction locally
run-VisitorCountPutFunction:
	@echo "Running the VisitorCountPutFunction locally..."
	sam local invoke VisitorCountPutFunction --event events/event.json