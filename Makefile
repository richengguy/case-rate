# The structure of this Makefile is based off of the one in Mozilla's ichanea
# project (https://github.com/mozilla/ichnaea/blob/32c757733c6edddb081346025ea6f64a86cfe12f/Makefile)

POSTCSS := NODE_ENV=production npx postcss
RENDER_TEMPLATE := python render_template.py
TYPESCRIPT := npx tsc
WEBPACK := npx webpack

.PHONY: help
help: default

.PHONY: default
default:
	@echo "Usage: make RULE"
	@echo ""
	@echo "report            - generate a case report"
	@echo ""
	@echo "assets            - compile all the static page assets"
	@echo "css               - compile app style sheets"
	@echo "html              - compile HTML from template files"
	@echo "js                - compile javascript"
	@echo ""
	@echo "clean             - clean all build artifacts"
	@echo "test              - run all app tests"


assets: html js css

report: assets
	@covid19 analyze \
		--min-confirmed 10 \
		--output dist/_analysis \
		--no-indent \
		-c Canada \
		-c Canada:Alberta \
		-c "Canada:British Columbia" \
		-c Canada:Manitoba \
		-c "Canada:New Brunswick" \
		-c "Canada:Newfoundland and Labrador" \
		-c "Canada:Nova Scotia" \
		-c Canada:Ontario \
		-c "Canada:Prince Edward Island" \
		-c Canada:Quebec \
		-c Canada:Saskatchewan \
		-c "Canada:Northwest Territories" \
		-c Canada:Nunavut \
		-c Canada:Yukon \
		-c US

.PHONY: clean
clean:
	@echo "-- Cleaning..."
	@rm -rf build
	@rm -rf dist

.PHONY: test
test:
	pytest

dist/.ignore:
	# @mkdir dist
	# @touch dist/.ignore

dist: dist/.ignore
	@echo '-- Make dist/ folder...'

# CSS

dist/style.css: dist postcss.config.js tailwind.config.js css/style.css
	@echo '-- Compiling $@...'
	@$(POSTCSS) css/style.css -o dist/style.css

css: dist/style.css

# HTML

dist/index.html: dist templates/base.jinja2 templates/dashboard.jinja2
	@echo "-- Rendering $@..."
	@$(RENDER_TEMPLATE) dashboard.jinja2 dist/index.html

dist/details.html: dist templates/base.jinja2 templates/details.jinja2
	@echo "-- Rendering $@..."
	@$(RENDER_TEMPLATE) details.jinja2 dist/details.html

html: dist/details.html dist/index.html

# Javascript

dist/dashboard.js dist/details.js: $(wildcard src/**/*.ts)
	@echo "-- Compiling $@..."
	@$(TYPESCRIPT)
	@$(WEBPACK)

js: dist/dashboard.js dist/details.js
