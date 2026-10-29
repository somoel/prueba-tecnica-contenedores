# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestViews(TransactionCase):
    def test_views_exist(self):
        self.env.ref("container_demurrage.view_demurrage_container_tree")
        self.env.ref("container_demurrage.view_demurrage_container_form")
        self.env.ref("container_demurrage.view_demurrage_container_search")
        self.env.ref("container_demurrage.view_demurrage_container_kanban")
        self.env.ref("container_demurrage.view_demurrage_container_pivot")
        self.env.ref("container_demurrage.view_demurrage_container_graph")
        self.env.ref("container_demurrage.view_demurrage_bl_tree")
        self.env.ref("container_demurrage.view_demurrage_bl_form")
        self.env.ref("container_demurrage.action_demurrage_container")
        self.env.ref("container_demurrage.menu_demurrage_root")
        self.env.ref("container_demurrage.menu_demurrage_config")

    def test_get_views(self):
        for vtype in ("form", "tree", "search"):
            self.env["demurrage.container"].get_view(view_type=vtype)

    def test_filters_in_arch(self):
        view = self.env.ref("container_demurrage.view_demurrage_container_search")
        arch = view.arch_db or ""
        self.assertIn("is_due_soon", arch)
        self.assertIn("is_overdue", arch)
        self.assertIn("missing_tariff", arch)

    def test_menus_exist(self):
        self.env.ref("container_demurrage.menu_demurrage_root")
        self.env.ref("container_demurrage.menu_demurrage_config")
