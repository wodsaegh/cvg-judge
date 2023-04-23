from colour import Color as Col


class Color(Col):

    def __init__(self, val: str):
        val = val.replace(" ", "")
        self.__dict__.__setitem__("alpha", 1.0)

        def parse_float(s: str):  # convert any number to float in range [0,1]
            if s.endswith("%"):
                return float(s[:-1]) / 100
            elif int(s[0]) > 0:
                return float(s) / 255
            else:
                return float(s)

        def parse_triple(s: str):
            ls = s[1:-1].split(",")
            if len(ls) != 3:
                raise ValueError()
            return tuple(parse_float(x) for x in ls[:3])

        def parse_quadruple(s: str):
            ls = s[1:-1].split(",")
            if len(ls) != 4:
                # not a quadruple, try parsing as a triple with alpha == 1
                return parse_triple(s), 1.0
            return tuple(parse_float(x) for x in ls[:3]), float(ls[3])

        if val.startswith("#"):
            if len(val[1:]) == 3 or len(val[1:]) == 6:  # hex is in web format
                super(Color, self).__init__(val)
            elif len(val[1:]) == 4:
                self.__dict__.__setitem__("alpha", int(val[-1:], 16) / 15)
                super(Color, self).__init__(val[:-1])
            elif len(val[1:]) == 8:
                self.__dict__.__setitem__("alpha", int(val[-2:], 16) / 255)
                super(Color, self).__init__(val[:-2])
        elif val.startswith("rgba"):
            triple, alpha = parse_quadruple(val[4:])
            super(Color, self).__init__(rgb=triple)
        elif val.startswith("rgb"):
            triple = parse_triple(val[3:])
            super(Color, self).__init__(rgb=triple)
        elif val.startswith("hsla"):
            triple, alpha = parse_quadruple(val[4:])
            super(Color, self).__init__(hsl=triple)
        elif val.startswith("hsl"):
            triple = parse_triple(val[3:])
            super(Color, self).__init__(hsl=triple)
        elif val[0].isalpha():
            super(Color, self).__init__(val)

    def __eq__(self, other):
        if other is None or type(other) != type(self):
            return False
        if self.alpha != other.alpha:
            return False
        return super(Color, self).__eq__(other)


