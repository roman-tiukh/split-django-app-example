import re
from django.apps import apps
from django.db import connection
from django.db.migrations import (
    CreateModel,
    DeleteModel,
    SeparateDatabaseAndState,
    Migration,
    RunPython,
)


CREATE = 1
DELETE = 2


class MoveModelsMigration(Migration):
    new_app_label = ''

    def __init__(self, name, app_label):
        super().__init__(name, app_label)
        moving_step = self.define_moving_step()
        state_operations = self.operations
        database_operations = []
        self.model_names = []

        if moving_step == DELETE:
            assert self.new_app_label and apps.is_installed(self.new_app_label)
            self.model_names = [operation.name for operation in state_operations
                                if isinstance(operation, DeleteModel)]

            database_operations.append(RunPython(
                code=self.move_models_from_app,
                reverse_code=self.move_models_from_app_reverse,
            ))

        self.operations = [
            SeparateDatabaseAndState(
                database_operations=database_operations,
                state_operations=state_operations,
            ),
        ]

    @staticmethod
    def get_move_models_sql(model_names: [str], old_app: str, new_app: str):
        model_names = set([model.lower() for model in model_names])
        old_app = old_app.lower()
        new_app = new_app.lower()
        sql = ''
        cursor = connection.cursor()
        for model in model_names:
            old_table_name = f'{old_app}_{model}'

            cursor.execute(f'''
                SELECT con.conname FROM pg_catalog.pg_constraint con
                INNER JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = '{old_table_name}' AND con.contype NOT IN ('p', 'u');
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

    def move_models_from_app(self, *args):
        with connection.cursor() as cursor:
            cursor.execute(self.get_move_models_sql(
                model_names=self.model_names,
                old_app=self.app_label,
                new_app=self.new_app_label,
            ))

    def move_models_from_app_reverse(self, *args):
        with connection.cursor() as cursor:
            cursor.execute(self.get_move_models_sql(
                model_names=self.model_names,
                old_app=self.new_app_label,
                new_app=self.app_label,
            ))

    def define_moving_step(self):
        has_delete_operations = False
        has_create_operations = False
        for operation in self.operations:
            if isinstance(operation, DeleteModel):
                has_delete_operations = True
            elif isinstance(operation, CreateModel):
                has_create_operations = True
        if has_delete_operations and has_create_operations:
            raise Exception('You have delete and create operations in one move-model migration')
        if has_delete_operations:
            return DELETE
        return CREATE
