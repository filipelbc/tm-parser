

class Bar:

    def __init__(self, x):
        self.x = x

    def __get__(self, *args):
        print('__get__', args)
        return self.x

    def __set__(self, *args):
        print('__set__', args)
        self.x = args[-1]


    d = 12


b = Bar(3)

print(b)


class Foo:
    bar = Bar(2)

    def __init__(self):
        print('foo')


f = Foo()

print(Foo.bar)
print(f.bar)

print('---')
f.bar = 4

print(Foo.bar)
print(f.bar)

print(getattr(f, 'bar'))

