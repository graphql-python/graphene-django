
def find_brakes(self, recursion):
    pass


REGEXES = [
    r'((?P<recursive_points>\*+)(?P<model_name>\s?\w+\s*)(?P<body>(\{|.*|\n*|\})*))',
    r'(\*node\s)*(\{(((?>[^{}]+)|(?R))*)\})',
]

query = """
query recursion_point {
    module {
        id
        name
        *module {
            edges {
                node {
                    id
                }
            }
        }
    }
}
"""

if __name__ == "__main__":

