import psycopg2

conn = psycopg2.connect(database="db_name",
                        host="db_host",
                        user="db_user",
                        password="db_pass",
                        port="5432")