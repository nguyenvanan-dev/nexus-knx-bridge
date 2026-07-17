export const showDialog = (title, message, type = 'info', onConfirm = null) => {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('show-dialog', {
            detail: { title, message, type, onConfirm }
        }));
    }
};

export const showToast = (message, type = 'success', duration = 3000) => {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message, type, duration }
        }));
    }
};
