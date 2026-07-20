# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime


class Deduplicator:
    def __init__(self, index_file='invoice_index.json'):
        self.index_file = index_file
        self.index = self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_index(self):
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def is_duplicate(self, invoice_number):
        return invoice_number in self.index

    def add_record(self, invoice_number, file_path):
        self.index[invoice_number] = {
            'file': file_path,
            'added_time': datetime.now().isoformat()
        }
        self._save_index()

    def get_existing(self, invoice_number):
        return self.index.get(invoice_number)
