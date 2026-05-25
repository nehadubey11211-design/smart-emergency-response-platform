//FILE: frontend/src/components/ErrorBoundary.jsx
// ==================================================
// Global Error Boundary Component
// ================================================== 
// This component catches JavaScript errors anywhere in its child component tree,
// logs those errors, and displays a fallback UI instead of the component tree that crashed.
// It also provides a "Retry" button to reset the error state and attempt to re-render the children.  

import { Component } from "react";

export default class ErrorBoundary extends Component {

  state = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error) {

    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, info) {

    console.error(
      "Error boundary caught:",
      error,
      info
    );

    // Future:
    // Send errors to Sentry / LogRocket / Datadog

  }

  handleRetry = () => {

    this.setState({
      hasError: false,
      error: null,
    });

  };

  render() {

    if (this.state.hasError) {

      return (

        <div
          className="
            flex min-h-screen flex-col
            items-center justify-center
            bg-[#0B1220]
            px-6 text-center
          "
        >

          <h2
            className="
              mb-4 text-3xl font-bold
              text-red-500
            "
          >
            Something went wrong
          </h2>

          <p
            className="
              mb-6 max-w-md text-gray-300
            "
          >
            An unexpected error occurred.
            Please try again.
          </p>

          <button
            onClick={this.handleRetry}
            className="
              rounded-xl bg-red-600
              px-5 py-3 font-medium
              text-white transition
              hover:bg-red-700
            "
          >
            Retry
          </button>

        </div>

      );
    }

    return this.props.children;
  }
}
