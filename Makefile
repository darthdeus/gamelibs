# Game Libraries Release Management
VERSION_FILE := .version
CURRENT_VERSION := $(shell if [ -f $(VERSION_FILE) ]; then cat $(VERSION_FILE); else echo "0.0.0"; fi)

# Parse current version
MAJOR := $(word 1,$(subst ., ,$(CURRENT_VERSION)))
MINOR := $(word 2,$(subst ., ,$(CURRENT_VERSION)))
PATCH := $(word 3,$(subst ., ,$(CURRENT_VERSION)))

# Calculate next version (bump patch by default)
NEXT_PATCH := $(shell echo $$(($(PATCH) + 1)))
NEXT_VERSION := $(MAJOR).$(MINOR).$(NEXT_PATCH)

.PHONY: help
help:
	@echo "Game Libraries Release Management"
	@echo "================================="
	@echo "Current version: v$(CURRENT_VERSION)"
	@echo ""
	@echo "Available commands:"
	@echo "  make release       - Create a new release (bumps patch version)"
	@echo "  make release-minor - Create a new release (bumps minor version)"
	@echo "  make release-major - Create a new release (bumps major version)"
	@echo "  make version       - Show current version"
	@echo "  make next-version  - Show what the next version will be"
	@echo ""

.PHONY: version
version:
	@echo "Current version: v$(CURRENT_VERSION)"

.PHONY: next-version
next-version:
	@echo "Next version will be: v$(NEXT_VERSION)"

.PHONY: release
release: check-git
	@echo "Creating release v$(NEXT_VERSION)..."
	@echo "$(NEXT_VERSION)" > $(VERSION_FILE)
	@git add $(VERSION_FILE)
	@git commit -m "Release v$(NEXT_VERSION)" || true
	@git tag -a "v$(NEXT_VERSION)" -m "Release v$(NEXT_VERSION) - Automated build of game libraries"
	@echo "✓ Created tag v$(NEXT_VERSION)"
	@echo ""
	@echo "Push the release with:"
	@echo "  git push origin main v$(NEXT_VERSION)"
	@echo ""
	@echo "Or use 'make push-release' to push automatically"

.PHONY: release-minor
release-minor: check-git
	$(eval NEXT_MINOR := $(shell echo $$(($(MINOR) + 1))))
	$(eval NEXT_VERSION := $(MAJOR).$(NEXT_MINOR).0)
	@echo "Creating minor release v$(NEXT_VERSION)..."
	@echo "$(NEXT_VERSION)" > $(VERSION_FILE)
	@git add $(VERSION_FILE)
	@git commit -m "Release v$(NEXT_VERSION)" || true
	@git tag -a "v$(NEXT_VERSION)" -m "Release v$(NEXT_VERSION) - Automated build of game libraries"
	@echo "✓ Created tag v$(NEXT_VERSION)"
	@echo ""
	@echo "Push the release with:"
	@echo "  git push origin main v$(NEXT_VERSION)"
	@echo ""
	@echo "Or use 'make push-release' to push automatically"

.PHONY: release-major
release-major: check-git
	$(eval NEXT_MAJOR := $(shell echo $$(($(MAJOR) + 1))))
	$(eval NEXT_VERSION := $(NEXT_MAJOR).0.0)
	@echo "Creating major release v$(NEXT_VERSION)..."
	@echo "$(NEXT_VERSION)" > $(VERSION_FILE)
	@git add $(VERSION_FILE)
	@git commit -m "Release v$(NEXT_VERSION)" || true
	@git tag -a "v$(NEXT_VERSION)" -m "Release v$(NEXT_VERSION) - Automated build of game libraries"
	@echo "✓ Created tag v$(NEXT_VERSION)"
	@echo ""
	@echo "Push the release with:"
	@echo "  git push origin main v$(NEXT_VERSION)"
	@echo ""
	@echo "Or use 'make push-release' to push automatically"

.PHONY: push-release
push-release:
	@echo "Pushing changes and tags to origin..."
	@git push origin main
	@git push origin --tags
	@echo "✓ Release pushed to GitHub"
	@echo ""
	@echo "Check the Actions tab on GitHub to monitor the build progress."

.PHONY: check-git
check-git:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Warning: You have uncommitted changes:"; \
		git status --short; \
		echo ""; \
		read -p "Continue anyway? [y/N] " -n 1 -r; \
		echo ""; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			echo "Aborted."; \
			exit 1; \
		fi \
	fi

.PHONY: init
init:
	@if [ ! -f $(VERSION_FILE) ]; then \
		echo "0.1.0" > $(VERSION_FILE); \
		echo "✓ Initialized version to v0.1.0"; \
	else \
		echo "Version file already exists: v$(CURRENT_VERSION)"; \
	fi

.PHONY: build
build:
	@echo "Building libraries locally..."
	@bash build_local.sh

.PHONY: clean
clean:
	@echo "Cleaning build directories..."
	@rm -rf build/
	@rm -rf prebuilt/
	@echo "✓ Clean complete"