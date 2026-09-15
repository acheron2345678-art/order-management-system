document.addEventListener("DOMContentLoaded", function () {

    const CSRF_COOKIE_NAME =
        "order_management_csrf_token";


    // =====================================================
    // CSRF
    // =====================================================

    function getCookie(name) {

        const cookies =
            document.cookie.split(";");


        for (const cookie of cookies) {

            const parts =
                cookie
                    .trim()
                    .split("=");


            const cookieName =
                parts.shift();


            const cookieValue =
                parts.join("=");


            if (cookieName === name) {

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


    function addTokenToForm(form) {

        const method = (
            form.method
            ||
            "get"
        ).toLowerCase();


        if (method === "get") {

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


    // =====================================================
    // CONFIRMATION DIALOG
    // =====================================================

    const dialog =
        document.createElement(
            "dialog"
        );


    dialog.className =
        "om-confirm-dialog";


    dialog.innerHTML = `
        <div class="om-confirm-card">

            <div class="om-confirm-icon">
                !
            </div>

            <div class="om-confirm-copy">

                <span class="om-confirm-eyebrow">
                    CONFIRM ACTION
                </span>

                <h2
                    id="om-confirm-title"
                    class="om-confirm-title"
                >
                    Are you sure?
                </h2>

                <p
                    id="om-confirm-message"
                    class="om-confirm-message"
                >
                </p>

            </div>

            <div class="om-confirm-actions">

                <button
                    type="button"
                    class="
                        btn
                        btn-outline-secondary
                    "
                    id="om-confirm-cancel"
                >
                    Cancel
                </button>

                <button
                    type="button"
                    class="
                        btn
                        btn-danger
                    "
                    id="om-confirm-submit"
                >
                    Confirm
                </button>

            </div>

        </div>
    `;


    dialog.setAttribute(
        "aria-labelledby",
        "om-confirm-title"
    );


    dialog.setAttribute(
        "aria-describedby",
        "om-confirm-message"
    );


    document.body.appendChild(
        dialog
    );


    const dialogTitle =
        document.getElementById(
            "om-confirm-title"
        );


    const dialogMessage =
        document.getElementById(
            "om-confirm-message"
        );


    const cancelButton =
        document.getElementById(
            "om-confirm-cancel"
        );


    const confirmButton =
        document.getElementById(
            "om-confirm-submit"
        );


    let pendingForm =
        null;


    let pendingSubmitter =
        null;


    // =====================================================
    // LEGACY confirm(...) SUPPORT
    // =====================================================

    function extractConfirmMessage(
        code
    ) {

        if (!code) {

            return null;

        }


        const match =
            code.match(
                /confirm\s*\(\s*(['"])(.*?)\1\s*\)/s
            );


        if (!match) {

            return null;

        }


        return match[2]
            .replace(
                /\\'/g,
                "'"
            )
            .replace(
                /\\"/g,
                '"'
            )
            .trim();

    }


    function convertLegacyConfirmations() {

        document
            .querySelectorAll(
                "form[onsubmit]"
            )
            .forEach(
                function (form) {

                    const code =
                        form.getAttribute(
                            "onsubmit"
                        );


                    if (
                        !code
                        ||
                        !code.includes(
                            "confirm("
                        )
                    ) {

                        return;

                    }


                    const message =
                        extractConfirmMessage(
                            code
                        );


                    if (message) {

                        form.dataset.confirmMessage =
                            message;

                    }


                    form.removeAttribute(
                        "onsubmit"
                    );

                }
            );


        document
            .querySelectorAll(
                'button[onclick*="confirm("]'
            )
            .forEach(
                function (button) {

                    const form =
                        button.closest(
                            "form"
                        );


                    if (!form) {

                        return;

                    }


                    const message =
                        extractConfirmMessage(
                            button.getAttribute(
                                "onclick"
                            )
                        );


                    if (message) {

                        form.dataset.confirmMessage =
                            message;

                    }


                    button.removeAttribute(
                        "onclick"
                    );

                }
            );

    }


    // =====================================================
    // INITIAL VALUES
    // =====================================================

    function rememberInitialValues() {

        document
            .querySelectorAll(
                'select[name="status"]'
            )
            .forEach(
                function (select) {

                    select.dataset.originalValue =
                        select.value;

                }
            );

    }


    // =====================================================
    // FORM HELPERS
    // =====================================================

    function getFormAction(
        form
    ) {

        try {

            return new URL(
                form.action,
                window.location.origin
            ).pathname;

        }

        catch {

            return (
                form.getAttribute(
                    "action"
                )
                ||
                ""
            );

        }

    }


    function getIntendedState(
        form
    ) {

        const stateInput =
            form.querySelector(
                '[name="state"]'
            );


        if (!stateInput) {

            return "";

        }


        return (
            stateInput.value
            ||
            ""
        )
            .trim()
            .toLowerCase();

    }


    function getStatusValue(
        form
    ) {

        const statusField =
            form.querySelector(
                '[name="status"]'
            );


        if (!statusField) {

            return "";

        }


        return (
            statusField.value
            ||
            ""
        )
            .trim()
            .toLowerCase();

    }


    function getOriginalStatusValue(
        form
    ) {

        const statusField =
            form.querySelector(
                '[name="status"]'
            );


        if (!statusField) {

            return "";

        }


        return (
            statusField.dataset.originalValue
            ||
            ""
        )
            .trim()
            .toLowerCase();

    }


    function getSubmitterText(
        submitter
    ) {

        if (!submitter) {

            return "";

        }


        const text =
            submitter.tagName
            ===
            "INPUT"
                ?
                submitter.value
                :
                submitter.textContent;


        return (
            text
            ||
            ""
        )
            .trim()
            .toLowerCase();

    }


    function findSubmitter(
        form,
        submitter
    ) {

        if (submitter) {

            return submitter;

        }


        return form.querySelector(
            `
            button[type="submit"]:not(:disabled),
            input[type="submit"]:not(:disabled)
            `
        );

    }


    // =====================================================
    // CONFIRMATION CONFIG
    // =====================================================

    function getConfirmationConfig(
        form,
        submitter
    ) {

        if (
            form.dataset.confirmMessage
        ) {

            return {

                title:
                    form.dataset.confirmTitle
                    ||
                    "Confirm action",

                message:
                    form.dataset.confirmMessage,

                confirmText:
                    form.dataset.confirmText
                    ||
                    "Confirm",

                tone:
                    form.dataset.confirmTone
                    ||
                    "danger"

            };

        }


        const action =
            getFormAction(
                form
            );


        const intendedState =
            getIntendedState(
                form
            );


        const submitterText =
            getSubmitterText(
                submitter
            );


        const status =
            getStatusValue(
                form
            );


        const originalStatus =
            getOriginalStatusValue(
                form
            );


        // =================================================
        // DELETE
        // =================================================

        if (
            action.includes(
                "/delete/"
            )
        ) {

            return {

                title:
                    "Delete this item?",

                message:
                    "This action permanently removes the record and cannot be undone.",

                confirmText:
                    "Delete",

                tone:
                    "danger"

            };

        }


        // =================================================
        // DEACTIVATE
        // =================================================

        if (
            action.includes(
                "/deactivate"
            )
        ) {

            return {

                title:
                    "Deactivate this item?",

                message:
                    "It will no longer be available for normal customer use until it is activated again.",

                confirmText:
                    "Deactivate",

                tone:
                    "danger"

            };

        }


        // =================================================
        // MERCHANT REASSIGNMENT
        // =================================================

        if (
            action.includes(
                "/admin/merchants/"
            )
            &&
            action.endsWith(
                "/reassign"
            )
        ) {

            return {

                title:
                    "Reassign this Merchant?",

                message:
                    "The Merchant will stop managing the current restaurant and will be linked to the newly selected restaurant instead.",

                confirmText:
                    "Reassign",

                tone:
                    "warning"

            };

        }


        // =================================================
        // EXPLICIT INACTIVE STATE
        // =================================================

        if (
            intendedState
            ===
            "inactive"
        ) {

            if (
                action.includes(
                    "/merchant/profile/status"
                )
            ) {

                return {

                    title:
                        "Deactivate restaurant?",

                    message:
                        "Customers will no longer be able to discover this restaurant until it is activated again.",

                    confirmText:
                        "Deactivate",

                    tone:
                        "danger"

                };

            }


            if (
                action.includes(
                    "/merchant/menu/"
                )
            ) {

                return {

                    title:
                        "Deactivate menu item?",

                    message:
                        "Customers will no longer be able to order this item until it is activated again.",

                    confirmText:
                        "Deactivate",

                    tone:
                        "danger"

                };

            }


            if (
                action.includes(
                    "/admin/merchants/"
                )
            ) {

                return {

                    title:
                        "Disable Merchant account?",

                    message:
                        "The Merchant will no longer be able to sign in. Their restaurant assignment will remain reserved.",

                    confirmText:
                        "Disable",

                    tone:
                        "danger"

                };

            }


            return {

                title:
                    "Disable this item?",

                message:
                    "This item will become unavailable until it is enabled again.",

                confirmText:
                    "Disable",

                tone:
                    "danger"

            };

        }


        // =================================================
        // ADMIN USER DISABLE
        // =================================================

        if (
            action.includes(
                "/admin/users/"
            )
            &&
            action.endsWith(
                "/toggle"
            )
            &&
            submitterText.includes(
                "disable"
            )
        ) {

            return {

                title:
                    "Disable user account?",

                message:
                    "The user will no longer be able to sign in until an administrator activates the account again.",

                confirmText:
                    "Disable",

                tone:
                    "danger"

            };

        }


        // =================================================
        // ADMIN RESTAURANT DISABLE
        // =================================================

        if (
            action.includes(
                "/admin/restaurants/"
            )
            &&
            action.endsWith(
                "/toggle"
            )
            &&
            submitterText.includes(
                "disable"
            )
        ) {

            return {

                title:
                    "Disable restaurant?",

                message:
                    "The restaurant will be hidden from customer discovery. Its menu data will remain stored.",

                confirmText:
                    "Disable",

                tone:
                    "danger"

            };

        }


        // =================================================
        // CANCEL ORDER
        // =================================================

        if (
            status
            ===
            "cancelled"
            &&
            originalStatus
            !==
            "cancelled"
        ) {

            return {

                title:
                    "Cancel this order?",

                message:
                    "Cancelling is a final workflow state and cannot be changed back through the normal order process.",

                confirmText:
                    "Cancel Order",

                tone:
                    "danger"

            };

        }


        // =================================================
        // TEXT FALLBACKS
        // =================================================

        if (
            submitterText.includes(
                "deactivate"
            )
        ) {

            return {

                title:
                    "Deactivate this item?",

                message:
                    "The item will become unavailable until it is activated again.",

                confirmText:
                    "Deactivate",

                tone:
                    "danger"

            };

        }


        if (
            submitterText.includes(
                "disable"
            )
        ) {

            return {

                title:
                    "Disable this item?",

                message:
                    "Access or availability will be disabled until this item is enabled again.",

                confirmText:
                    "Disable",

                tone:
                    "danger"

            };

        }


        return null;

    }


    // =====================================================
    // OPEN CONFIRMATION
    // =====================================================

    function openConfirmation(
        form,
        submitter,
        config
    ) {

        pendingForm =
            form;


        pendingSubmitter =
            submitter;


        dialogTitle.textContent =
            config.title
            ||
            "Confirm action";


        dialogMessage.textContent =
            config.message
            ||
            "Are you sure you want to continue?";


        confirmButton.textContent =
            config.confirmText
            ||
            "Confirm";


        dialog.dataset.tone =
            config.tone
            ||
            "danger";


        confirmButton.classList.remove(
            "btn-danger",
            "btn-warning",
            "btn-primary"
        );


        if (
            config.tone
            ===
            "warning"
        ) {

            confirmButton.classList.add(
                "btn-warning"
            );

        }

        else if (
            config.tone
            ===
            "primary"
        ) {

            confirmButton.classList.add(
                "btn-primary"
            );

        }

        else {

            confirmButton.classList.add(
                "btn-danger"
            );

        }


        dialog.showModal();


        cancelButton.focus();

    }


    function closeConfirmation() {

        if (
            dialog.open
        ) {

            dialog.close();

        }


        pendingForm =
            null;


        pendingSubmitter =
            null;

    }


    confirmButton.addEventListener(
        "click",

        function () {

            if (
                !pendingForm
            ) {

                closeConfirmation();

                return;

            }


            const form =
                pendingForm;


            const submitter =
                pendingSubmitter;


            dialog.close();


            pendingForm =
                null;


            pendingSubmitter =
                null;


            form.dataset.confirmBypass =
                "true";


            if (
                typeof form.requestSubmit
                ===
                "function"
            ) {

                if (
                    submitter
                ) {

                    form.requestSubmit(
                        submitter
                    );

                }

                else {

                    form.requestSubmit();

                }

            }

            else {

                form.submit();

            }

        }
    );


    cancelButton.addEventListener(
        "click",
        closeConfirmation
    );


    dialog.addEventListener(
        "cancel",

        function (event) {

            event.preventDefault();


            closeConfirmation();

        }
    );


    dialog.addEventListener(
        "click",

        function (event) {

            if (
                event.target
                ===
                dialog
            ) {

                closeConfirmation();

            }

        }
    );


    // =====================================================
    // UI-6
    // LOADING / ACTION STATES
    // =====================================================

    function getLoadingText(
        form,
        submitter
    ) {

        if (
            submitter
            &&
            submitter.dataset.loadingText
        ) {

            return (
                submitter.dataset.loadingText
            );

        }


        if (
            form.dataset.loadingText
        ) {

            return (
                form.dataset.loadingText
            );

        }


        const text =
            getSubmitterText(
                submitter
            );


        const action =
            getFormAction(
                form
            ).toLowerCase();


        // =================================================
        // AUTH
        // =================================================

        if (
            text.includes(
                "sign in"
            )
        ) {

            return "Signing in...";

        }


        if (
            text.includes(
                "logout"
            )
            ||
            text.includes(
                "sign out"
            )
        ) {

            return "Signing out...";

        }


        // =================================================
        // CHECKOUT
        // =================================================

        if (
            text.includes(
                "place order"
            )
            ||
            text.includes(
                "checkout"
            )
            ||
            text.includes(
                "submit project request"
            )
            ||
            text.includes(
                "complete order"
            )
        ) {

            return "Processing...";

        }


        // =================================================
        // INVENTORY
        // =================================================

        if (
            text.includes(
                "restock"
            )
            ||
            action.includes(
                "restock"
            )
        ) {

            return "Restocking...";

        }


        // =================================================
        // CART
        // =================================================

        if (
            text.includes(
                "add to cart"
            )
            ||
            text
            ===
            "add"
            ||
            text.startsWith(
                "+ add"
            )
        ) {

            return "Adding...";

        }


        // =================================================
        // CREATE
        // =================================================

        if (
            text.includes(
                "create"
            )
            ||
            text.includes(
                "register"
            )
        ) {

            return "Creating...";

        }


        // =================================================
        // SAVE
        // =================================================

        if (
            text.includes(
                "save"
            )
            ||
            text.includes(
                "adjustment"
            )
        ) {

            return "Saving...";

        }


        // =================================================
        // UPDATE
        // =================================================

        if (
            text.includes(
                "update"
            )
            ||
            text.includes(
                "apply"
            )
        ) {

            return "Updating...";

        }


        // =================================================
        // REASSIGN
        // =================================================

        if (
            text.includes(
                "reassign"
            )
        ) {

            return "Reassigning...";

        }


        // =================================================
        // DELETE
        // =================================================

        if (
            text.includes(
                "delete"
            )
        ) {

            return "Deleting...";

        }


        // =================================================
        // REMOVE
        // =================================================

        if (
            text.includes(
                "remove"
            )
        ) {

            return "Removing...";

        }


        // =================================================
        // CLEAR CART
        // =================================================

        if (
            text.includes(
                "clear cart"
            )
        ) {

            return "Clearing...";

        }


        // =================================================
        // DEACTIVATE
        // =================================================

        if (
            text.includes(
                "deactivate"
            )
        ) {

            return "Deactivating...";

        }


        // =================================================
        // DISABLE
        // =================================================

        if (
            text.includes(
                "disable"
            )
        ) {

            return "Disabling...";

        }


        // =================================================
        // ACTIVATE / ENABLE
        // =================================================

        if (
            text.includes(
                "activate"
            )
            ||
            text.includes(
                "enable"
            )
        ) {

            return "Activating...";

        }


        // =================================================
        // CANCEL
        // =================================================

        if (
            text.includes(
                "cancel"
            )
        ) {

            return "Cancelling...";

        }


        return "Processing...";

    }


    // =====================================================
    // STORE ORIGINAL BUTTON STATE
    // =====================================================

    function storeSubmitterState(
        submitter
    ) {

        if (
            !submitter
            ||
            submitter.dataset.omOriginalStored
            ===
            "true"
        ) {

            return;

        }


        submitter.dataset.omOriginalStored =
            "true";


        if (
            submitter.tagName
            ===
            "INPUT"
        ) {

            submitter.dataset.omOriginalValue =
                submitter.value;

        }

        else {

            submitter.dataset.omOriginalHtml =
                submitter.innerHTML;

        }

    }


    // =====================================================
    // SET BUTTON LOADING
    // =====================================================

    function setSubmitterLoading(
        submitter,
        loadingText
    ) {

        if (
            !submitter
        ) {

            return;

        }


        storeSubmitterState(
            submitter
        );


        submitter.classList.add(
            "om-button-loading"
        );


        submitter.setAttribute(
            "aria-busy",
            "true"
        );


        submitter.setAttribute(
            "aria-disabled",
            "true"
        );


        if (
            submitter.tagName
            ===
            "INPUT"
        ) {

            submitter.value =
                loadingText;

        }

        else {

            submitter.innerHTML = `

                <span
                    class="om-button-spinner"
                    aria-hidden="true"
                >
                </span>

                <span>
                    ${loadingText}
                </span>

            `;

        }

    }


    // =====================================================
    // RESTORE BUTTON
    // =====================================================

    function restoreSubmitter(
        submitter
    ) {

        if (
            !submitter
        ) {

            return;

        }


        submitter.classList.remove(
            "om-button-loading"
        );


        submitter.removeAttribute(
            "aria-busy"
        );


        submitter.removeAttribute(
            "aria-disabled"
        );


        submitter.disabled =
            false;


        if (
            submitter.tagName
            ===
            "INPUT"
        ) {

            if (
                submitter.dataset.omOriginalValue
                !==
                undefined
            ) {

                submitter.value =
                    submitter.dataset.omOriginalValue;

            }

        }

        else if (
            submitter.dataset.omOriginalHtml
            !==
            undefined
        ) {

            submitter.innerHTML =
                submitter.dataset.omOriginalHtml;

        }

    }


    // =====================================================
    // SET FORM LOADING
    // =====================================================

    function setFormLoadingState(
        form,
        submitter
    ) {

        const method = (
            form.method
            ||
            "get"
        ).toLowerCase();


        /*
            Search/filter GET forms stay instant.
            We don't want a loader flashing during
            normal filtering/navigation.
        */

        if (
            method
            ===
            "get"
        ) {

            return;

        }


        const resolvedSubmitter =
            findSubmitter(
                form,
                submitter
            );


        form.dataset.omSubmitting =
            "true";


        form.classList.add(
            "om-form-submitting"
        );


        form.setAttribute(
            "aria-busy",
            "true"
        );


        if (
            resolvedSubmitter
        ) {

            const loadingText =
                getLoadingText(
                    form,
                    resolvedSubmitter
                );


            setSubmitterLoading(
                resolvedSubmitter,
                loadingText
            );


            /*
                Delay actual disabling until after
                the native submission has begun.

                This avoids losing a submit button's
                name/value from submitted form data.
            */

            window.setTimeout(
                function () {

                    resolvedSubmitter.disabled =
                        true;

                },

                0
            );

        }

    }


    // =====================================================
    // RESET STATES
    // =====================================================

    function resetLoadingStates() {

        document
            .querySelectorAll(
                "form.om-form-submitting"
            )
            .forEach(
                function (form) {

                    delete form.dataset.omSubmitting;


                    form.classList.remove(
                        "om-form-submitting"
                    );


                    form.removeAttribute(
                        "aria-busy"
                    );

                }
            );


        document
            .querySelectorAll(
                ".om-button-loading"
            )
            .forEach(
                function (submitter) {

                    restoreSubmitter(
                        submitter
                    );

                }
            );

    }


    /*
        Browsers can preserve DOM state when navigating
        back using the back/forward cache.

        Restore buttons so they don't remain disabled.
    */

    window.addEventListener(
        "pageshow",

        function () {

            resetLoadingStates();

        }
    );


    // =====================================================
    // FORM SUBMIT INTERCEPTION
    // =====================================================

    document.addEventListener(
        "submit",

        function (event) {

            const form =
                event.target;


            if (
                !form
                ||
                form.tagName
                !==
                "FORM"
            ) {

                return;

            }


            const submitter =
                findSubmitter(
                    form,
                    event.submitter
                    ||
                    null
                );


            // =================================================
            // PREVENT DOUBLE SUBMISSION
            // =================================================

            if (
                form.dataset.omSubmitting
                ===
                "true"
            ) {

                event.preventDefault();

                return;

            }


            // =================================================
            // ALREADY CONFIRMED
            // =================================================

            if (
                form.dataset.confirmBypass
                ===
                "true"
            ) {

                delete form.dataset.confirmBypass;


                setFormLoadingState(
                    form,
                    submitter
                );


                return;

            }


            // =================================================
            // CHECK FOR CONFIRMATION
            // =================================================

            const config =
                getConfirmationConfig(
                    form,
                    submitter
                );


            if (
                config
            ) {

                event.preventDefault();


                openConfirmation(
                    form,
                    submitter,
                    config
                );


                return;

            }


            // =================================================
            // NORMAL SUBMISSION
            // =================================================

            setFormLoadingState(
                form,
                submitter
            );

        }
    );


    // =====================================================
    // INITIALIZE
    // =====================================================

    convertLegacyConfirmations();


    rememberInitialValues();

});