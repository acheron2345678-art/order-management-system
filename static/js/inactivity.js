document.addEventListener(
    "DOMContentLoaded",
    function () {

        const modal =
            document.getElementById(
                "inactivity-modal"
            );

        const okButton =
            document.getElementById(
                "inactivity-modal-ok"
            );


        if (
            !modal
            ||
            !okButton
        ) {
            return;
        }


        const INACTIVITY_LIMIT_MS =
            30 * 60 * 1000;


        // For testing:
        // const INACTIVITY_LIMIT_MS =
        //     1 * 60 * 1000;


        const ACTIVITY_THROTTLE_MS =
            1000;


        let inactivityTimer =
            null;

        let lastActivity =
            Date.now();

        let lastActivityHandledAt =
            0;

        let logoutStarted =
            false;


        function scheduleTimer() {

            if (logoutStarted) {
                return;
            }


            if (inactivityTimer) {

                clearTimeout(
                    inactivityTimer
                );

            }


            const elapsed =
                Date.now()
                -
                lastActivity;


            const remaining =
                INACTIVITY_LIMIT_MS
                -
                elapsed;


            if (remaining <= 0) {

                logoutDueToInactivity();

                return;

            }


            inactivityTimer =
                setTimeout(
                    logoutDueToInactivity,
                    remaining
                );

        }


        function registerActivity() {

            if (logoutStarted) {
                return;
            }


            const now =
                Date.now();


            if (
                now
                -
                lastActivityHandledAt
                <
                ACTIVITY_THROTTLE_MS
            ) {
                return;
            }


            lastActivityHandledAt =
                now;


            lastActivity =
                now;


            scheduleTimer();

        }


        async function logoutDueToInactivity() {

            if (logoutStarted) {
                return;
            }


            logoutStarted =
                true;


            if (inactivityTimer) {

                clearTimeout(
                    inactivityTimer
                );

            }


            const csrfToken =
                typeof window.getCsrfToken
                === "function"

                    ? window.getCsrfToken()

                    : null;


            const headers = {};


            if (csrfToken) {

                headers[
                    "X-CSRF-Token"
                ] = csrfToken;

            }


            try {

                const response =
                    await fetch(
                        "/logout",
                        {
                            method:
                                "POST",

                            credentials:
                                "same-origin",

                            cache:
                                "no-store",

                            headers:
                                headers
                        }
                    );


                if (!response.ok) {

                    console.warn(
                        "Automatic logout returned status:",
                        response.status
                    );

                }

            }

            catch (error) {

                console.error(
                    "Automatic logout request failed:",
                    error
                );

            }


            document.body.classList.add(
                "inactivity-locked"
            );


            modal.classList.add(
                "show"
            );


            okButton.focus();

        }


        const activityEvents = [

            "mousedown",

            "mousemove",

            "keydown",

            "click",

            "scroll",

            "touchstart"

        ];


        activityEvents.forEach(
            function (eventName) {

                window.addEventListener(
                    eventName,
                    registerActivity,
                    {
                        passive: true
                    }
                );

            }
        );


        document.addEventListener(
            "visibilitychange",
            function () {

                if (
                    !document.hidden
                ) {

                    const elapsed =
                        Date.now()
                        -
                        lastActivity;


                    if (
                        elapsed
                        >=
                        INACTIVITY_LIMIT_MS
                    ) {

                        logoutDueToInactivity();

                        return;

                    }


                    scheduleTimer();

                }

            }
        );


        window.addEventListener(
            "focus",
            function () {

                const elapsed =
                    Date.now()
                    -
                    lastActivity;


                if (
                    elapsed
                    >=
                    INACTIVITY_LIMIT_MS
                ) {

                    logoutDueToInactivity();

                    return;

                }


                scheduleTimer();

            }
        );


        okButton.addEventListener(
            "click",
            function () {

                window.location.replace(
                    "/login"
                );

            }
        );


        scheduleTimer();

    }
); 