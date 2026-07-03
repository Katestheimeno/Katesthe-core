/**
 * Copy Field Functionality - Enhanced Version
 * Handles click-to-copy functionality for copyable fields in Django admin
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle all copy fields
    const copyFields = document.querySelectorAll('.copy-field, .code-copy');

    copyFields.forEach(function(element) {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const value = this.getAttribute('data-code');

            if (!value) {
                showToast('No value to copy!', 'error');
                return;
            }

            // Check if clipboard API is available
            if (!navigator.clipboard) {
                fallbackCopy(value);
                return;
            }

            navigator.clipboard.writeText(value).then(function() {
                // Store original state
                const originalHTML = element.innerHTML;
                const originalClass = element.className;

                // Show success state
                element.innerHTML = '✓ Copied!';
                element.className = originalClass + ' copied';

                // Show subtle toast notification
                showToast('Copied!', 'success');

                // Restore original state after 1.5 seconds
                setTimeout(() => {
                    element.innerHTML = originalHTML;
                    element.className = originalClass;
                }, 1500);

            }).catch(function(err) {
                // Show error state
                const originalHTML = element.innerHTML;
                const originalClass = element.className;

                element.innerHTML = '✗ Failed';
                element.className = originalClass + ' error';

                showToast('Copy failed!', 'error');

                // Restore original state after 1.5 seconds
                setTimeout(() => {
                    element.innerHTML = originalHTML;
                    element.className = originalClass;
                }, 1500);
            });
        });
    });
});

/**
 * Fallback copy method for browsers without clipboard API
 */
function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        showToast('Value copied to clipboard!', 'success');
    } catch (err) {
        showToast('Failed to copy to clipboard!', 'error');
    }

    document.body.removeChild(textArea);
}

/**
 * Show subtle toast notification
 */
function showToast(message, type = 'success') {
    // Create toast element
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 8px 16px;
        border-radius: 4px;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px;
        font-weight: 400;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        max-width: 200px;
        text-align: center;
    `;

    // Set colors based on type
    if (type === 'success') {
        toast.style.backgroundColor = '#d4edda';
        toast.style.color = '#155724';
        toast.style.border = '1px solid #c3e6cb';
    } else if (type === 'error') {
        toast.style.backgroundColor = '#f8d7da';
        toast.style.color = '#721c24';
        toast.style.border = '1px solid #f5c6cb';
    }

    toast.innerHTML = message;
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
    }, 10);

    // Remove after delay
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.addEventListener('transitionend', () => {
            if (toast.parentNode) {
                toast.remove();
            }
        });
    }, 2000);
}
