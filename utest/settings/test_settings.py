#  Copyright 2008 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from __future__ import with_statement

import unittest
import os
from robotide.preferences import settings

from robotide.preferences.settings import Settings, SectionError,\
    ConfigurationError, initialize_settings, SettingsMigrator, Excludes

from resources.setting_utils import TestSettingsHelper


class TestInvalidSettings(TestSettingsHelper):

    def test_no_settings_exists(self):
        self.assertEquals(self.settings._config_obj, {})

    def test_setting_name_with_space(self):
        self.settings['name with space'] = 0
        settings = Settings(self.user_settings_path)
        self.assertEquals(settings['name with space'], 0)

    def test_invalid_settings(self):
        self._write_settings('invalid syntax = foo')
        self.assertRaises(ConfigurationError, Settings, self.user_settings_path)


class TestSettingTypes(TestSettingsHelper):

    def test_writing_string_setting(self):
        self._test_settings_types({'string':'value'})

    def test_writing_unicode_setting(self):
        self._test_settings_types({'unicode_string':u'non-ascii character \xe4'})

    def test_writing_list_setting(self):
        self._test_settings_types({'unicode_string': [1, 'string',
                                                u'non-ascii character \xe4']})

    def test_writing_tuple_setting(self):
        self._test_settings_types({'unicode_string': (1, 'string',
                                                u'non-ascii character \xe4')})

    def test_writing_dictionary_setting(self):
        self._test_settings_types({'dictionary': {'a': 1, 'b': 2, 'c': 3}})

    def test_writing_none_setting(self):
        self._test_settings_types({'none': None})

    def test_writing_boolean_setting(self):
        self._test_settings_types({'boolean': True})

    def test_writing_multiline_string_setting(self):
        multiline = u"""Multi line string
with non-ascii chars \xe4
and quotes "foo" 'bar'
and even triple quotes \"\"\" '''
"""
        self._test_settings_types({'multiline': multiline})

    def test_multiple_settings(self):
        multiline = u"""Multi line string
with non-ascii chars \xe4
and quotes "foo" 'bar'
and even triple quotes \"\"\" '''
"""
        self._test_settings_types({'multiline': multiline, 'string': u'some',
                                'bool': False, 'int':1, 'float':2.4})

    def _test_settings_types(self, expected):
        for key, value in expected.items():
            self.settings[key] = value
        self.assertEqual(expected, self._read_settings()._config_obj)


class TestSettings(TestSettingsHelper):

    def test_changing_settings_with_setitem(self):
        self._create_settings_with_defaults()
        self.settings['foo'] = 'new value'
        self._check_content({'foo':'new value', 'hello':'world'})

    def test_getting_settings_with_getitem(self):
        self._create_settings_with_defaults()
        self.assertEquals('bar', self.settings['foo'])

    def _create_settings_with_defaults(self):
        self._write_settings("foo = 'bar'\nhello = 'world'", self.user_settings_path)
        self.default = {'foo':'bar', 'hello':'world'}
        self.settings = Settings(self.user_settings_path)

    def test_set(self):
        self._create_settings_with_defaults()
        self.settings.set('foo', 'new value')
        self._check_content({'foo':'new value', 'hello':'world'})

    def test_set_with_non_existing_value(self):
        self._create_settings_with_defaults()
        self.settings.set('zip', 2)
        self._check_content({'foo':'bar', 'hello':'world', 'zip':2})

    def test_set_without_autosave(self):
        self._create_settings_with_defaults()
        self.settings.set('foo', 'new value', autosave=False)
        self._check_content(self.default, check_self_settings=False)
        expected = {'foo':'new value', 'hello':'world'}
        self.assertEquals(self.settings._config_obj, expected)
        self.settings.save()
        self._check_content(expected)

    def test_set_without_override_when_settings_does_not_exist(self):
        self.settings.set('foo', 'new value', override=False)
        self._check_content({'foo':'new value'})

    def test_set_without_override_when_settings_exists(self):
        self._create_settings_with_defaults()
        self.settings.set('foo', 'new value', override=False)
        self._check_content(self.default)

    def test_set_values(self):
        self._create_settings_with_defaults()
        self.settings.set_values({'foo':'new value', 'int':1})
        self._check_content({'foo':'new value', 'hello':'world', 'int':1})

    def test_set_values_without_autosave(self):
        self._create_settings_with_defaults()
        self.settings.set_values({'foo':'new value', 'int':1}, autosave=False)
        expected = {'foo':'new value', 'hello':'world', 'int':1}
        self.assertEquals(self.settings._config_obj, expected)
        self._check_content(self.default, check_self_settings=False)
        self.settings.save()
        self._check_content(expected)

    def test_set_values_without_override(self):
        self._create_settings_with_defaults()
        self.settings.set_values({'foo':'not set', 'new item': 'is set'},
                                 override=False)
        self.default['new item'] = 'is set'
        self._check_content(self.default)

    def test_set_values_with_none(self):
        self._create_settings_with_defaults()
        self.settings.set_values(None)
        self._check_content(self.default)

    def test_set_defaults(self):
        self.settings.set_defaults(foo='bar', zip=3)
        self._check_content({'foo':'bar', 'zip':3})

    def test_set_defaults_when_some_values_already_exists(self):
        self._create_settings_with_defaults()
        self.settings.set_defaults(foo='value', zip=3)
        self._check_content({'foo':'bar', 'hello':'world', 'zip':3})


SETTINGS_CONTENT = """
# Main comment
string = 'REPLACE_STRING'
int = 13
float = 1.5
# Main comment 2
boolean = True

[Section 1]
# Section 1 comment

list = [1, 2]
robot = 'REPLACE_ROBOT'
tuple = (1, 2)

# Section 1 comment 2

[Section 2]

list = [2, 1]
# Comment again
tuple = (2, 1)

# Which also may be several lines
"""


class TestSettingsFileContent(TestSettingsHelper):

    def test_settings_file_content_stay(self):
        self._write_settings(SETTINGS_CONTENT)
        settings = Settings(self.user_settings_path)
        settings['string'] = 'new value'
        settings['Section 1']['robot'] = 'New Robot'
        expected = SETTINGS_CONTENT.replace('REPLACE_STRING', 'new value')
        expected = expected.replace('REPLACE_ROBOT', 'New Robot')
        self.assertEquals(self._read_settings_file_content(), expected)


class TestSections(TestSettingsHelper):

    def test_add_section(self):
        self.settings.add_section('Plugin 1')
        self.assertEquals(self.settings['Plugin 1']._config_obj, {})

    def test_add_section_returns_section(self):
        self.assertEquals(self.settings.add_section('Plugin 1')._config_obj, {})

    def test_add_section_with_default_values(self):
        section = self.settings.add_section('Plugin 1', a='b', one='2')
        self.assertEquals(section._config_obj, {'a':'b', 'one':'2'})
        self.assertEquals(self._read_settings()['Plugin 1']._config_obj,
                          {'a':'b', 'one':'2'})

    def test_add_section_should_not_fail_if_section_already_exists(self):
        self.settings.add_section('Plugin 1')
        self.settings.add_section('Plugin 1')
        self.settings['Plugin 1']['foo'] = 'bar'
        self.assertEquals(self.settings.add_section('Plugin 1')._config_obj,
                          {'foo':'bar'})

    def test_add_section_should_fail_if_item_with_same_name_already_exists(self):
        self.settings['Plugin 1'] = 123
        self.assertRaises(SectionError, self.settings.add_section, 'Plugin 1')

    def test_set_should_fail_if_section_with_same_name_already_exists(self):
        self.settings.add_section('Plugin 1')
        self.assertRaises(SectionError, self.settings.set, 'Plugin 1', 123)

    def test_set_overriding_section_with_other_section(self):
        self.settings.add_section('Plugin 1', foo='bar', hello='world')
        section = self.settings.add_section('Plugin 2', zip=2)
        self.settings.set('Plugin 1', section)
        self.assertEquals(self.settings['Plugin 1']._config_obj, {'zip':2})
        self.assertEquals(self._read_settings()['Plugin 1']._config_obj, {'zip':2})

    def test_set_updating_section_with_other_section(self):
        self.settings.add_section('Plugin 1', foo='bar', hello='world')
        section = self.settings.add_section('Plugin 2', foo='new value', zip=2)
        self.settings.set('Plugin 1', section, override=False)
        expected = {'foo':'bar', 'hello':'world', 'zip':2}
        self.assertEquals(self.settings['Plugin 1']._config_obj, expected)
        self.assertEquals(self._read_settings()['Plugin 1']._config_obj, expected)

    def test_add_sub_section(self):
        self.settings.add_section('Plugin 1')
        self.settings['Plugin 1'].add_section('Plugin 1.1')
        self.assertEquals(self.settings['Plugin 1']['Plugin 1.1']._config_obj, {})

    def test_add_settings_to_sub_section(self):
        self.settings.add_section('Plugin 1')
        self.settings['Plugin 1'].add_section('Plugin 1.1')
        self.settings['Plugin 1']['Plugin 1.1']['foo'] = 'bar'
        self.assertEquals(self.settings['Plugin 1']['Plugin 1.1']._config_obj,
                          {'foo':'bar'})

    def test_using_section_separately_and_saving(self):
        self.settings.add_section('Plugin 1')
        plugin_settings = self.settings['Plugin 1']
        plugin_settings['foo'] = 'bar'
        plugin_settings.save()
        self.assertEquals(self._read_settings()['Plugin 1']._config_obj,
                          {'foo':'bar'})

    def test_set_values_to_section(self):
        defaults = {'foo':'bar', 'hello':'world'}
        self.settings.add_section('Plugin 1')
        self.settings['Plugin 1'].set_values(defaults)
        self.assertEquals(self._read_settings()['Plugin 1']._config_obj, defaults)


class TestInitializeSettings(TestSettingsHelper):

    def setUp(self):
        self._orig_dir = settings.SETTINGS_DIRECTORY
        self.settings_dir = os.path.join(os.path.dirname(__file__), 'ride')
        settings.SETTINGS_DIRECTORY = self.settings_dir
        self._init_settings_paths()
        self._write_settings("foo = 'bar'\nhello = 'world'",
                             self.settings_path)
        self.user_settings_path = os.path.join(self.settings_dir, 'user.cfg')

    def tearDown(self):
        settings.SETTINGS_DIRECTORY = self._orig_dir
        self._remove_path(self.user_settings_path)
        os.removedirs(self.settings_dir)

    def test_initialize_settings_creates_directory(self):
        initialize_settings('user settings', self.settings_path, 'user.cfg')
        self.assertTrue(os.path.exists(self.settings_dir))

    def test_initialize_settings_copies_settings(self):
        initialize_settings('user settings', self.settings_path, 'user.cfg')
        self.assertTrue(os.path.exists(self.settings_dir))

    def test_initialize_settings_does_merge_when_settings_exists(self):
        os.mkdir(self.settings_dir)
        self._write_settings("foo = 'bar'\nhello = 'world'",self.settings_path)
        self._write_settings("foo = 'new value'\nhello = 'world'",
                             self.user_settings_path)
        initialize_settings('user settings', self.settings_path, 'user.cfg')
        self._check_content({'foo':'new value', 'hello' : 'world',
                             SettingsMigrator.SETTINGS_VERSION:SettingsMigrator.CURRENT_SETTINGS_VERSION,}, False)

    def test_initialize_settings_raises_exception_when_invalid_user_settings(self):
        os.mkdir(self.settings_dir)
        self._write_settings("foo = 'bar'\nhello = 'world'",
                             self.settings_path)
        self._write_settings("invalid = invalid", self.user_settings_path)
        self.assertRaises(ConfigurationError, initialize_settings, 'user settings',
                          self.settings_path, 'user.cfg')

    def test_initialize_settings_replaces_corrupted_settings_with_defaults(self):
        os.mkdir(self.settings_dir)
        self._write_settings("dlskajldsjjw2018032")
        defaults = self._read_file(self.settings_path)
        settings = self._read_file(initialize_settings('user settings', self.settings_path, 'user.cfg'))
        self.assertEqual(defaults, settings)

    def _read_file(self, path):
        with open(path, 'r') as o:
            return o.read()

class TestMergeSettings(TestSettingsHelper):

    def setUp(self):
        self._init_settings_paths()
        self._write_settings("foo = 'bar'\nhello = 'world'",
                             self.settings_path)

    def test_merge_when_no_user_settings(self):
        SettingsMigrator(self.settings_path, self.user_settings_path).merge()
        self._check_content({'foo':'bar', 'hello' : 'world'}, False)

    def test_merge_when_user_settings_are_changed(self):
        self._write_settings("foo = 'new value'\nhello = 'world'",
                             self.user_settings_path)
        SettingsMigrator(self.settings_path, self.user_settings_path).merge()
        self._check_content({'foo':'new value', 'hello' : 'world'}, False)

    def test_merge_when_new_settings_in_defaults(self):
        self._write_settings("foo = 'bar'\nhello = 'world'\nnew = 'value'",
                             self.settings_path)
        self._write_settings("foo = 'new value'\nhello = 'world'",
                             self.user_settings_path)
        SettingsMigrator(self.settings_path, self.user_settings_path).merge()
        self._check_content({'foo':'new value', 'hello' : 'world', 'new':'value'},
                            False)

    def test_merge_fails_reasonably_when_settings_file_is_read_only(self):
        try:
            SettingsMigrator(self.settings_path, self.read_only_path).merge()
        except RuntimeError, e:
            self.assertTrue(str(e).startswith('Could not open'))
        else:
            raise AssertionError('merging read-only file succeeded')

class TestExcludes(unittest.TestCase):

    class FakeSettings(object):
        def __init__(self, setting):
            self.get_without_default = lambda _: setting
            self.add_change_listener = lambda _: 0

    def tearDown(self):
        if hasattr(self, 'file_path') and os.path.exists(self.file_path):
            os.remove(self.file_path)

    def test_excludes_init_work(self):
        fs = self.FakeSettings('test_excludes_work')
        e = Excludes(fs)
        self.assertEqual('test_excludes_work', e._project_name)

    def test_update_excludes(self):
        fs = self.FakeSettings('test_update_excludes')
        e = Excludes(fs)
        e.update_excludes(['foo'])
        self.file_path = os.path.join(e._dir_for_settings, 'test_update_excludes')
        self._verify_exclude_file(self.file_path, ['foo\n'])

    def test_updating_excludes_does_not_repeat_path(self):
        fs = self.FakeSettings('test_update_repeat')
        e = Excludes(fs)
        e.update_excludes(['foo'])
        e.update_excludes(['foo'])
        self.file_path = os.path.join(e._dir_for_settings, 'test_update_repeat')
        self._verify_exclude_file(self.file_path, ['foo\n'])

    def test_updating_excludes_does_not_repeat_almost_similar_paths(self):
        fs = self.FakeSettings('test_repeat_almost_similar')
        e = Excludes(fs)
        e.update_excludes(['/foo/bar'])
        e.update_excludes(['/foo/bar/'])
        self.file_path = os.path.join(e._dir_for_settings, 'test_repeat_almost_similar')
        self._verify_exclude_file(self.file_path, ['/foo/bar\n'])

    def test_check_path(self):
        fs = self.FakeSettings('test_check_path')
        e = Excludes(fs)
        e.update_excludes(['/foo/bar/baz'])
        self.assertTrue(e.check_path('/foo/bar/baz'))
        self.file_path = os.path.join(e._dir_for_settings, 'test_check_path')
        self._verify_exclude_file(self.file_path, ['/foo/bar/baz\n'])

    def test_check_path_when_file_is_in_excluded_directory(self):
        fs = self.FakeSettings('test_file_in_excluded_dir')
        e = Excludes(fs)
        e.update_excludes(['/foo'])
        self.assertTrue(e.check_path('/foo/bar/baz'))
        self.assertTrue(e.check_path('/foo/bar/'))
        self.assertTrue(e.check_path('/foo/'))
        self.file_path = os.path.join(e._dir_for_settings, 'test_file_in_excluded_dir')
        self._verify_exclude_file(self.file_path, ['/foo\n'])

    def test_directory_changed(self):
        fs = self.FakeSettings('test_dir_changed')
        e = Excludes(fs)
        file_paths = [ os.path.join(e._dir_for_settings, 'test_dir_changed'),
                       os.path.join(e._dir_for_settings, 'test_dir_changed_to_another_one') ]
        self.assertEqual(e._project_name, 'test_dir_changed')
        self.assertEqual(e._exclude_file_path, file_paths[0])
        e.setting_changed('default directory', file_paths[0], file_paths[1])
        self.assertEqual(e._project_name, 'test_dir_changed_to_another_one')
        self.assertEqual(e._exclude_file_path, file_paths[1])

    def _verify_exclude_file(self, file_path, expected):
        file_contents = open(file_path, 'r').readlines()
        self.assertEqual(file_contents, expected)

if __name__ == "__main__":
    unittest.main()
