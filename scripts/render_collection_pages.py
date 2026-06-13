#!/usr/bin/env python3

from render_readme_catalog import main as render_readme_catalog
from render_site_nav import main as render_site_nav


def main():
    render_readme_catalog()
    render_site_nav()


if __name__ == "__main__":
    main()
