from setuptools import find_packages, setup

setup(
    name="daylily_carrier_tracking",
    version="0.1.0",
    description="Unified multi-carrier tracking (FedEx implemented; UPS/USPS pending)",
    packages=find_packages(),
    install_requires=[
        "requests",
        "yaml_config_day",
    ],
    entry_points={
        "console_scripts": [
            "tracking_day = daylily_carrier_tracking.cli:main",
        ],
    },
)
