# coding: utf-8


from http import HTTPStatus


import flask
import werkzeug.exceptions as http_exceptions


class JsonHttpException(http_exceptions.HTTPException):
    def __init__(self, code, headers=None):
        super().__init__()

        self.code = code
        self.headers = headers

    def build_json_reponse(self, name, description):
        response = flask.jsonify(
            status_code=self.code,
            name=name,
            description=description
        )
        response.status_code = self.code

        if self.headers:
            for name, value in self.headers.items():
                response.headers[name] = value

        return response


def abort(code, headers=None):
    raise JsonHttpException(code, headers)


class JsonHttpExceptionHandler:
    def init(self, app):
        for code in http_exceptions.default_exceptions.keys():
            app.register_error_handler(
                code, JsonHttpExceptionHandler._make_error_response
            )

    @classmethod
    def _make_error_response(cls, ex):
        if isinstance(ex, JsonHttpException):
            return cls._make_response(ex)
        elif isinstance(ex, http_exceptions.HTTPException):
            return cls._make_response(
                JsonHttpException(ex.code)
            )
        else:
            return cls._make_response(
                JsonHttpException(HTTPStatus.INTERNAL_SERVER_ERROR)
            )

    @classmethod
    def _make_response(cls, json_exception):
        default_exception_class = http_exceptions.default_exceptions[
            json_exception.code
        ]
        default_exception = default_exception_class()

        return json_exception.build_json_reponse(
            default_exception.name,
            default_exception.description
        )

