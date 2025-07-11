from camel.societies.workforce import Workforce
workforce = Workforce("Test")
print([method for method in dir(workforce) if not method.startswith('_')])