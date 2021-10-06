import re
from django.db import connection


def get_split_app_sql(model_names: [str], old_app: str, new_app: str):
    old_app = old_app.lower()
    new_app = new_app.lower()
    sql = ''
    cursor = connection.cursor()
    for model in set(model_names):
        model = model.lower()
        old_table_name = f'{old_app}_{model}'

        cursor.execute(f'''
            SELECT con.conname FROM pg_catalog.pg_constraint con
            INNER JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = '{old_table_name}' AND con.contype != 'p';
        ''')
        constraints = [c[0] for c in cursor.fetchall()]

        cursor.execute(f"SELECT indexname FROM pg_indexes WHERE tablename = '{old_table_name}';")
        indexes = [c[0] for c in cursor.fetchall()]

        for constraint in constraints:
            new_con_name = re.sub(f'^{old_app}', new_app, constraint)
            sql += f'ALTER TABLE {old_table_name} RENAME CONSTRAINT {constraint} TO {new_con_name};\n'

        for index in indexes:
            new_index_name = re.sub(f'^{old_app}', new_app, index)
            sql += f'ALTER INDEX {index} RENAME TO {new_index_name};\n'

        sql += f'ALTER TABLE {old_app}_{model} RENAME TO {new_app}_{model};\n'

        sql += f"UPDATE django_content_type SET app_label='{new_app}' " \
               f"WHERE app_label='{old_app}' AND model='{model}';\n"
    cursor.close()
    return sql
