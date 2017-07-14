# PLEASE PUT ALL FUNCTIONS WHICH PERFORM GENERAL FORMATTING ON ANY DATATYPE WITHOUT USING ANY
# MODULES RELATED TO THE EVENT-SYSTEM i.e FUNCTIONS RELATED TO DB MODELS, OTHER API MODULES
# OR OTHER HELPER MODULES
import bleach


def dasherize(text):
    return text.replace('_', '-')


def string_empty(string):
    if type(string) is not str and type(string) is not unicode:
        return False
    if string and string.strip() and string != u'' and string != u' ':
        return False
    else:
        return True


def strip_tags(html):
    return bleach.clean(html, tags=[], attributes={}, styles=[], strip=True)
