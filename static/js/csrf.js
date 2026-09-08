document.addEventListener(
    "DOMContentLoaded",
    function () {

        const CSRF_COOKIE_NAME =
            "order_management_csrf_token";


        function getCookie(name) {

            const cookies =
                document.cookie.split(";");


            for (
                const cookie of cookies
            ) {

                const parts =
                    cookie
                        .trim()
                        .split("=");


                const cookieName =
                    parts.shift();


                const cookieValue =
                    parts.join("=");


                if (
                    cookieName === name
                ) {

                    return decodeURIComponent(
                        cookieValue
                    );

                }

            }


            return null;

        }


        function getCsrfToken() {

            return getCookie(
                CSRF_COOKIE_NAME
            );

        }


        function addTokenToForm(
            form
        ) {

            const method = (
                form.method
                ||
                "get"
            ).toLowerCase();


            if (
                method === "get"
            ) {

                return;

            }


            const csrfToken =
                getCsrfToken();


            if (!csrfToken) {

                console.warn(
                    "CSRF token cookie not found."
                );

                return;

            }


            let input =
                form.querySelector(
                    'input[name="csrf_token"]'
                );


            if (!input) {

                input =
                    document.createElement(
                        "input"
                    );

                input.type =
                    "hidden";

                input.name =
                    "csrf_token";

                form.appendChild(
                    input
                );

            }


            input.value =
                csrfToken;

        }


        document
            .querySelectorAll(
                "form"
            )
            .forEach(
                function (form) {

                    addTokenToForm(
                        form
                    );

                }
            );


        document.addEventListener(
            "submit",
            function (event) {

                const form =
                    event.target;


                if (
                    form
                    &&
                    form.tagName
                    ===
                    "FORM"
                ) {

                    addTokenToForm(
                        form
                    );

                }

            },
            true
        );


        window.getCsrfToken =
            getCsrfToken;

    }
);