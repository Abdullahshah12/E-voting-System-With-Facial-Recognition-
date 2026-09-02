// Main JavaScript file for E-Voting System

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
});

// Form validation helpers
function validateCNIC(cnic) {
    const pattern = /^[0-9]{5}-[0-9]{7}-[0-9]{1}$/;
    return pattern.test(cnic);
}

function validateMobile(mobile) {
    const pattern = /^[0-9]{4}-[0-9]{7}$/;
    return pattern.test(mobile);
}

// Add input formatting for CNIC and Mobile
document.addEventListener('DOMContentLoaded', function() {
    const cnicInput = document.getElementById('cnic');
    if (cnicInput) {
        cnicInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 0) {
                if (value.length <= 5) {
                    value = value;
                } else if (value.length <= 12) {
                    value = value.substring(0, 5) + '-' + value.substring(5);
                } else {
                    value = value.substring(0, 5) + '-' + value.substring(5, 12) + '-' + value.substring(12, 13);
                }
            }
            e.target.value = value;
        });
    }
    
    const mobileInput = document.getElementById('mobile');
    if (mobileInput) {
        mobileInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 0) {
                if (value.length <= 4) {
                    value = value;
                } else {
                    value = value.substring(0, 4) + '-' + value.substring(4, 11);
                }
            }
            e.target.value = value;
        });
    }
    
    // OTP input formatting
    const otpInput = document.getElementById('otp');
    if (otpInput) {
        otpInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/\D/g, '').substring(0, 6);
        });
    }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading state to forms
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
            submitBtn.disabled = true;
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Processing...';
            
            // Re-enable after 10 seconds as fallback
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }, 10000);
        }
    });
});

// Prevent multiple form submissions
let formSubmitted = false;
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        if (formSubmitted) {
            e.preventDefault();
            return false;
        }
        formSubmitted = true;
        setTimeout(() => {
            formSubmitted = false;
        }, 3000);
    });
});

// Animated Word Cloud 3D Effect
document.addEventListener('DOMContentLoaded', function() {
    const wordCloud = document.getElementById('word-cloud-bg');
    if (!wordCloud) return;

    const words = document.querySelectorAll('.word:not(.main-word)');
    
    // Add 3D rotation effect on mouse move
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    document.addEventListener('mousemove', function(e) {
        mouseX = (e.clientX / window.innerWidth) - 0.5;
        mouseY = (e.clientY / window.innerHeight) - 0.5;
    });

    // Smooth animation loop
    function animate() {
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        const container = document.querySelector('.word-cloud-container');
        if (container) {
            container.style.transform = `
                rotateY(${targetX * 10}deg) 
                rotateX(${-targetY * 10}deg)
            `;
        }

        // Add parallax effect to individual words
        words.forEach((word, index) => {
            const speed = parseFloat(word.getAttribute('data-speed')) || 1;
            const x = targetX * speed * 20;
            const y = targetY * speed * 20;
            const currentTransform = word.style.transform || '';
            
            // Preserve existing transforms and add parallax
            if (!currentTransform.includes('translate3d')) {
                word.style.transform = `translate3d(${x}px, ${y}px, 0)`;
            }
        });

        requestAnimationFrame(animate);
    }

    animate();

    // Add random subtle movements
    words.forEach((word, index) => {
        setInterval(() => {
            const randomX = (Math.random() - 0.5) * 10;
            const randomY = (Math.random() - 0.5) * 10;
            const randomRotate = (Math.random() - 0.5) * 5;
            
            word.style.transition = 'transform 2s ease-in-out';
            const currentTransform = word.style.transform || '';
            word.style.transform = `${currentTransform} translate(${randomX}px, ${randomY}px) rotate(${randomRotate}deg)`;
        }, 3000 + index * 500);
    });

    // Add glow pulse effect
    setInterval(() => {
        const randomWord = words[Math.floor(Math.random() * words.length)];
        randomWord.style.transition = 'all 0.5s ease';
        randomWord.style.textShadow = `
            0 0 40px rgba(0, 212, 255, 1),
            0 0 80px rgba(0, 212, 255, 0.7)
        `;
        
        setTimeout(() => {
            randomWord.style.textShadow = `
                0 0 20px rgba(0, 212, 255, 0.5),
                0 0 40px rgba(0, 212, 255, 0.3)
            `;
        }, 500);
    }, 2000);
});
