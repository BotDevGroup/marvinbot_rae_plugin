from distutils.core import setup
from setuptools import find_packages

REQUIREMENTS = [
    'marvinbot',
    'bs4'
]

setup(name='marvinbot-rae-plugin',
      version='0.1',
      description='Buscar definiciones en la Real Academia Española.',
      author='Conrado Reyes',
      author_email='coreyes@gmail.com',
      url='',
      packages=[
        'marvinbot_rae_plugin',
      ],
      package_dir={
        'marvinbot_rae_plugin':'marvinbot_rae_plugin'
      },
      zip_safe=False,
      include_package_data=True,
      package_data={'': ['*.ini']},
      install_requires=REQUIREMENTS,
      dependency_links=[
          'git+ssh://git@github.com:BotDevGroup/marvin.git#egg=marvinbot',
      ],
)
