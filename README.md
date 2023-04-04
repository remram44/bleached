# bleached

This is a small HTML checker. It can validate that HTML code is safe.

It does not aim to support the entire HTML spec, rather it focuses on checking HTML that has been run through a sanitizer (such as [bleach](https://github.com/mozilla/bleach)).

## How to use?

```
$ pip install bleached
$ python3
>>> import bleached
>>> bleached.is_html_bleached('<p>Hello world</p>')
True
>>> bleached.is_html_bleached('<script>alert("Hello world");</script>')
False
>>> bleached.check_html('<p>Hello world</p>')
>>> bleached.check_html('<script>alert("Hello world");</script>')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
bleached.UnsafeInput: Line 1 character 8 (input index 7): Found forbidden opening tag 'script'
```

## Why use this?

[bleach](https://github.com/mozilla/bleach) is a great library for sanitizing untrusted HTML. You should use it instead of this where possible.

However, it offers no way to check that a piece of HTML has been sanitized. Running the HTML through bleach again will only work if you have the exact same version, as bleach makes no guarantee of stability of their input. This is where bleached is useful.

## Warnings

* No validation of attributes is performed. If you choose to allow an attribute, it is up to you to validate the values.
* This accepts a much smaller subset of HTML than web browsers. Be ready for false negatives if you use this to validate HTML documents.
