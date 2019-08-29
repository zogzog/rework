from setuptools import setup


setup(name='rework',
      version='0.9.0',
      author='Aurelien Campeas',
      author_email='aurelien.campeas@pythonian.fr',
      description='A database-oriented distributed task dispatcher',
      url='https://bitbucket.org/pythonian/rework',
      packages=['rework'],
      install_requires=[
          'psutil',
          'colorama',
          'sqlalchemy',
          'sqlhelp',
          'psycopg2',
          'pystuck',
          'click',
          'tzlocal == 1.5.1',
          'inireader'
      ],
      extra_require=[
          'pytest',
          'pytest_sa_pg'
      ],
      entry_points={
          'console_scripts': [
              'rework=rework.cli:rework'
          ]
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Database',
          'Topic :: System :: Distributed Computing',
          'Topic :: Software Development :: Object Brokering'
      ]
)
