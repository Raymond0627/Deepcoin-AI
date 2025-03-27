import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

const FetchingPrediction = ({ 
  text = "Fetching prediction...",
  typingSpeed = 100,
  deletingSpeed = 50,
  pauseDuration = 500,
  loaderColor = "white",
  textColor = "white"
}) => {
  const [displayedText, setDisplayedText] = useState(text[0]); // Keep first character
  const [index, setIndex] = useState(1); // Start from second character
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (isPaused) return;

    const speed = isDeleting ? deletingSpeed : typingSpeed;
    const timeout = setTimeout(() => {
      if (!isDeleting && index < text.length) {
        // Typing effect
        setDisplayedText((prev) => prev + text[index]);
        setIndex(index + 1);
      } else if (isDeleting && index > 1) {
        // Deleting effect (keep first character)
        setDisplayedText((prev) => prev.slice(0, -1));
        setIndex(index - 1);
      } else {
        // Switch between typing and deleting
        setIsPaused(true);
        setTimeout(() => {
          setIsDeleting(!isDeleting);
          setIsPaused(false);
        }, pauseDuration);
      }
    }, speed);

    return () => clearTimeout(timeout);
  }, [index, isDeleting, isPaused, text, typingSpeed, deletingSpeed, pauseDuration]);

  return (
    <div style={{ 
      marginTop: "10px", 
      color: textColor, 
      display: "flex", 
      alignItems: "center",
      fontFamily: "monospace", // Better for loading text
      justifyContent : "center",
      fontSize : "20px"
    }}>
      <span 
        className="loader" 
        style={{ 
          marginRight: "10px",
          borderColor: loaderColor,
          borderRightColor: "transparent" // For spinner effect
        }}
      ></span>
      <span>{displayedText}</span>
    </div>
  );
};

FetchingPrediction.propTypes = {
  text: PropTypes.string,
  typingSpeed: PropTypes.number,
  deletingSpeed: PropTypes.number,
  pauseDuration: PropTypes.number,
  loaderColor: PropTypes.string,
  textColor: PropTypes.string
};

export default FetchingPrediction;